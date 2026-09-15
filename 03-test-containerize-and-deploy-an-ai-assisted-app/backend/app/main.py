"""FastAPI application for the Card Catalog backend.

Routes implement `../openapi.yaml`. All persistence goes through a `CardStore`
(see `app/store.py`). `create_app` accepts one so tests can inject a store;
with no store it lazily builds a SQLAlchemy store on the configured database
(SQLite by default) — lazily, so merely importing this module touches no disk.

The app is password-gated (see `app/auth.py`): every `/api/cards*` route
requires a valid session cookie, obtained via `POST /api/login`. `create_app`
also accepts an `AuthConfig` so tests can use a fixed test password instead
of real environment variables.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import APIRouter, Cookie, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.auth import COOKIE_NAME, AuthConfig, LoginRequest, RateLimiter, default_auth_config
from app.db import init_db, make_engine, make_session_factory
from app.models import Card, CardCreate, CardMove, CardUpdate
from app.seed import seed_if_empty
from app.sqlalchemy_store import SqlAlchemyCardStore
from app.store import CardStore

load_dotenv()  # backend/.env, if present — see .env.example. No-op if missing.

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")


def _default_store() -> CardStore:
    """A SQLAlchemy store on the configured database (SQLite by default)."""
    engine = make_engine()
    init_db(engine)
    store = SqlAlchemyCardStore(make_session_factory(engine))
    seed_if_empty(store)
    return store


def create_app(
    store: CardStore | None = None, auth_config: AuthConfig | None = None
) -> FastAPI:
    holder: dict[str, CardStore | None] = {"store": store}
    # Resolved lazily, same reasoning as the store: merely importing this
    # module (e.g. `from app.main import create_app`) must not require real
    # AUTH_* environment variables to be set. `lifespan` below still resolves
    # it eagerly at server boot, so a real deployment fails fast on startup,
    # not on the first request.
    auth_holder: dict[str, AuthConfig | None] = {"config": auth_config}
    limiter_holder: dict[str, RateLimiter | None] = {"limiter": None}

    def get_store() -> CardStore:
        if holder["store"] is None:
            holder["store"] = _default_store()
        return holder["store"]

    def get_auth() -> AuthConfig:
        if auth_holder["config"] is None:
            auth_holder["config"] = default_auth_config()
        return auth_holder["config"]

    def get_limiter() -> RateLimiter:
        if limiter_holder["limiter"] is None:
            config = get_auth()
            limiter_holder["limiter"] = RateLimiter(
                config.max_attempts, config.window_seconds
            )
        return limiter_holder["limiter"]

    def require_auth(
        session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    ) -> None:
        if not get_auth().verify_session_token(session):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        get_store()  # build + seed the store when the server boots, not per request
        get_auth()  # fail fast on missing AUTH_* config, not on the first request
        yield

    app = FastAPI(
        title="Card Catalog API",
        version="0.1.0",
        summary="REST API for the Card Catalog mini Kanban board.",
        lifespan=lifespan,
    )

    # A session cookie is credentialed, so the CORS origin list must be exact
    # (browsers refuse `allow_origins=["*"]` together with allow_credentials).
    # Same-origin deployments (the frontend proxied to /api by nginx or Vite)
    # never hit this at all — it only matters if frontend and backend are ever
    # served from different origins.
    origins = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # --- Auth: public endpoints (no session required to reach them) ---

    @app.post("/api/login", tags=["auth"])
    def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, bool]:
        auth = get_auth()
        limiter = get_limiter()
        client_key = request.client.host if request.client else "unknown"
        if not limiter.allow(client_key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Try again in a few minutes.",
            )
        if not auth.verify_password(payload.password):
            limiter.record_failure(client_key)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
            )
        limiter.record_success(client_key)
        response.set_cookie(
            key=COOKIE_NAME,
            value=auth.make_session_token(),
            max_age=auth.session_ttl_seconds,
            httponly=True,
            secure=auth.cookie_secure,
            samesite="lax",
            path="/",
        )
        return {"authenticated": True}

    @app.post("/api/logout", tags=["auth"])
    def logout(response: Response) -> dict[str, bool]:
        response.delete_cookie(COOKIE_NAME, path="/")
        return {"authenticated": False}

    @app.get("/api/session", tags=["auth"])
    def session_status(
        session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    ) -> dict[str, bool]:
        return {"authenticated": get_auth().verify_session_token(session)}

    # --- Cards: every route below requires a valid session ---

    cards = APIRouter(dependencies=[Depends(require_auth)])

    @cards.get("/api/cards", response_model=list[Card], tags=["cards"])
    def list_cards(store: CardStore = Depends(get_store)) -> list[Card]:
        return store.list_cards()

    @cards.post(
        "/api/cards",
        response_model=Card,
        status_code=status.HTTP_201_CREATED,
        tags=["cards"],
    )
    def create_card(
        payload: CardCreate, store: CardStore = Depends(get_store)
    ) -> Card:
        return store.create_card(payload)

    @cards.get("/api/cards/{card_id}", response_model=Card, tags=["cards"])
    def get_card(card_id: str, store: CardStore = Depends(get_store)) -> Card:
        card = store.get_card(card_id)
        if card is None:
            raise _NOT_FOUND
        return card

    @cards.patch("/api/cards/{card_id}", response_model=Card, tags=["cards"])
    def update_card(
        card_id: str,
        payload: CardUpdate,
        store: CardStore = Depends(get_store),
    ) -> Card:
        card = store.update_card(card_id, payload)
        if card is None:
            raise _NOT_FOUND
        return card

    @cards.delete(
        "/api/cards/{card_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["cards"],
    )
    def delete_card(
        card_id: str, store: CardStore = Depends(get_store)
    ) -> Response:
        if not store.delete_card(card_id):
            raise _NOT_FOUND
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @cards.post(
        "/api/cards/{card_id}/move",
        response_model=list[Card],
        tags=["cards"],
    )
    def move_card(
        card_id: str,
        payload: CardMove,
        store: CardStore = Depends(get_store),
    ) -> list[Card]:
        cards_out = store.move_card(card_id, payload)
        if cards_out is None:
            raise _NOT_FOUND
        return cards_out

    app.include_router(cards)

    return app


app = create_app()
