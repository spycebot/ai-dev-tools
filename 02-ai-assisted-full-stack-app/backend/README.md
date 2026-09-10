# Card Catalog — Backend

FastAPI service implementing the REST contract in [`../openapi.yaml`](../openapi.yaml).

Persistence goes through the `CardStore` interface (`app/store.py`). The default
is `SqlAlchemyCardStore` (`app/sqlalchemy_store.py`) on the database named by
`DATABASE_URL` — SQLite (`sqlite:///./card_catalog.db`) unless overridden.
`InMemoryCardStore` remains as the reference implementation and is used in tests.
The column/position rules both stores rely on live in `app/board.py`.

See the top-level [`../README.md`](../README.md) for the full picture (including
the PostgreSQL swap).

## Quick reference

```bash
uv sync                                   # install deps into .venv
uv run pytest                             # run the test suite (both stores)
uv run uvicorn app.main:app --reload      # dev server on http://localhost:8000

# use a different database:
DATABASE_URL="sqlite:///./scratch.db" uv run uvicorn app.main:app
```

Interactive API docs (when the server is running): http://localhost:8000/docs

The dev database file `card_catalog.db` is created on first run and is
git-ignored. Delete it to reset to the seed cards.
