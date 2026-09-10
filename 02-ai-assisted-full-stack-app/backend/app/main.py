"""FastAPI application for the Card Catalog backend.

Routes implement `../openapi.yaml`. All persistence goes through a `CardStore`
(see `app/store.py`); `create_app` accepts one so tests can inject a fresh
in-memory store per test.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.models import Card, CardCreate, CardMove, CardUpdate
from app.store import CardStore, InMemoryCardStore

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")


def create_app(store: CardStore | None = None) -> FastAPI:
    card_store: CardStore = store if store is not None else InMemoryCardStore()

    app = FastAPI(
        title="Card Catalog API",
        version="0.1.0",
        summary="REST API for the Card Catalog mini Kanban board.",
    )

    # Single-user app, no credentials — a wide-open CORS policy is fine and
    # keeps step 4 (wiring the frontend in) friction-free.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_store() -> CardStore:
        return card_store

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/cards", response_model=list[Card], tags=["cards"])
    def list_cards(store: CardStore = Depends(get_store)) -> list[Card]:
        return store.list_cards()

    @app.post(
        "/api/cards",
        response_model=Card,
        status_code=status.HTTP_201_CREATED,
        tags=["cards"],
    )
    def create_card(
        payload: CardCreate, store: CardStore = Depends(get_store)
    ) -> Card:
        return store.create_card(payload)

    @app.get("/api/cards/{card_id}", response_model=Card, tags=["cards"])
    def get_card(card_id: str, store: CardStore = Depends(get_store)) -> Card:
        card = store.get_card(card_id)
        if card is None:
            raise _NOT_FOUND
        return card

    @app.patch("/api/cards/{card_id}", response_model=Card, tags=["cards"])
    def update_card(
        card_id: str,
        payload: CardUpdate,
        store: CardStore = Depends(get_store),
    ) -> Card:
        card = store.update_card(card_id, payload)
        if card is None:
            raise _NOT_FOUND
        return card

    @app.delete(
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

    @app.post(
        "/api/cards/{card_id}/move",
        response_model=list[Card],
        tags=["cards"],
    )
    def move_card(
        card_id: str,
        payload: CardMove,
        store: CardStore = Depends(get_store),
    ) -> list[Card]:
        cards = store.move_card(card_id, payload)
        if cards is None:
            raise _NOT_FOUND
        return cards

    return app


app = create_app()
