# Card Catalog — Backend

FastAPI service implementing the REST contract in [`../openapi.yaml`](../openapi.yaml).

At this stage (homework step 3) persistence is a **mock in-memory data store**
(`app/store.py`). Step 5 swaps it for a SQLAlchemy-backed store implementing the
same `CardStore` interface, with no route changes.

See the top-level [`../README.md`](../README.md) for install and run instructions.

## Quick reference

```bash
uv sync                                   # install deps into .venv
uv run pytest                             # run the test suite
uv run uvicorn app.main:app --reload      # dev server on http://localhost:8000
```

Interactive API docs (when the server is running): http://localhost:8000/docs
