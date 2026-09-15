# Card Catalog — Backend

FastAPI service implementing the REST contract in [`../openapi.yaml`](../openapi.yaml).

Persistence goes through the `CardStore` interface (`app/store.py`). The default
is `SqlAlchemyCardStore` (`app/sqlalchemy_store.py`) on the database named by
`DATABASE_URL` — SQLite (`sqlite:///./card_catalog.db`) unless overridden.
`InMemoryCardStore` remains as the reference implementation and is used in tests.
The column/position rules both stores rely on live in `app/board.py`.

See the top-level [`../README.md`](../README.md) for the full picture (including
the PostgreSQL swap).

## Authentication

The app is gated by one shared password (see `app/auth.py`) — no user
accounts, no database. Every `/api/cards*` route requires a signed session
cookie, obtained via `POST /api/login`. The server **refuses to start**
unless `AUTH_PASSWORD_HASH` and `AUTH_SECRET_KEY` are set — generate both
with:

```bash
uv run python scripts/set_password.py
```

Paste the two printed lines into `backend/.env` (copy `.env.example` first if
you don't have one yet), then start/restart the server. See `.env.example`
for the full list of `AUTH_*` / `CORS_ORIGINS` variables and what they do.

## Quick reference

```bash
uv sync                                   # install deps into .venv
uv run pytest                             # run the test suite (both stores)
uv run python scripts/set_password.py     # generate/rotate the shared password
uv run uvicorn app.main:app --reload      # dev server on http://localhost:8000

# use a different database:
DATABASE_URL="sqlite:///./scratch.db" uv run uvicorn app.main:app
```

Interactive API docs (when the server is running): http://localhost:8000/docs

The dev database file `card_catalog.db` is created on first run and is
git-ignored. Delete it to reset to the seed cards.
