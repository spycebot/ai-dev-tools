# Card Catalog

A mini Kanban board for tracking personal tasks across three stages — **To Do**, **In Progress**, and **Done** — styled after the ["living paper"](https://shannonware.com) design language: an old computer-manual look built from index cards on aged paper.

This is homework assignment 2 for the [AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp) course. The entire application — spec, frontend, backend, and database — is being built end-to-end with an AI coding agent (Claude Code), in stepwise fashion, with a commit + push after each completed step.

The full product specification lives at [`_docs/specs.md`](./_docs/specs.md). Read that document for complete functional requirements, the data model, and design details — this README focuses on what the app is, how it's built, and how to run it.

## Status

This project is being built in five stages. Current progress:

- [x] **1. Product specification** — see [`_docs/specs.md`](./_docs/specs.md)
- [x] **2. Frontend prototype** (mocked backend) — in `frontend/`
- [x] **3. Backend** (FastAPI, mock data store) — in `backend/`, contract in [`openapi.yaml`](./openapi.yaml)
- [x] **4. Connect frontend and backend** — `frontend/src/api/cards.js` now makes real HTTP calls, proxied to the backend by Vite
- [x] **5. Database** (SQLite via SQLAlchemy) — `SqlAlchemyCardStore` is now the default; data persists to `backend/card_catalog.db`

**All five stages are complete.** The app is a working full stack: a React board → a FastAPI service → a SQLAlchemy-backed SQLite database. The persistence layer is chosen behind the `CardStore` interface, so pointing it at PostgreSQL is a `DATABASE_URL` change plus a driver install — no application code. **Both servers must be running** (see [Running the App](#running-the-app)).

## Feature Summary

- Single user, no login, one board, three fixed columns (no custom columns).
- Cards have a title (required), description, due date, and priority (low/medium/high).
- Create, edit, and delete cards (delete requires confirmation — no undo).
- Drag-and-drop to move cards between columns and to reorder cards within a column.
- Column headers show a live card count.
- Cards past their due date (and not in Done) are visually flagged as overdue.

See [`_docs/specs.md`](./_docs/specs.md) for full detail on each of these.

## Tech Stack

| Layer            | Choice                                            | Notes                                                                 |
|-------------------|----------------------------------------------------|------------------------------------------------------------------------|
| Frontend          | React + Vite (Node.js)                            | Drag-and-drop via a library such as `@dnd-kit`.                        |
| Backend           | Python + FastAPI, managed with `uv`               | Tests written before implementation.                                  |
| API contract      | `openapi.yaml`                                    | Source of truth between frontend and backend.                         |
| Database (dev)    | SQLite                                             | Accessed through SQLAlchemy so the backend stays database-agnostic.   |
| Database (future) | PostgreSQL                                         | Swap-in target once the app is stable, no application code changes.   |
| Styling           | Custom CSS ("living paper" theme)                 | Special Elite (body) and Share Tech Mono (data/labels) fonts, aged-paper CSS background, blueprint blue (`#18385a`) and annotation amber (`#7a5c0a`) accent colors. |

## Project Structure

```
02-ai-assisted-full-stack-app/
├── AGENTS.md          # Instructions for the AI coding agent building this project
├── README.md          # This file
├── openapi.yaml       # REST contract between frontend and backend (source of truth)
├── _docs/
│   └── specs.md       # Full product specification
├── frontend/          # React + Vite app
│   ├── vite.config.js        # Dev server + /api → backend proxy
│   ├── .env.example          # VITE_BACKEND_URL (proxy target) override
│   └── src/
│       ├── api/cards.js       # The only module that talks to the backend (fetch)
│       ├── components/        # Column, CardItem, CardEditor
│       ├── App.jsx            # Board state, drag-and-drop wiring
│       ├── App.css            # "Living paper" theme (layout + components)
│       └── index.css          # Aged-paper background, fonts, color tokens
└── backend/           # FastAPI app (uv-managed)
    ├── pyproject.toml         # Dependencies + pytest config
    ├── card_catalog.db        # Dev SQLite database (git-ignored, created on first run)
    ├── app/
    │   ├── main.py            # FastAPI app + routes (create_app factory)
    │   ├── models.py          # Pydantic schemas (Card, CardCreate, CardUpdate, CardMove)
    │   ├── board.py           # Pure column/position rules, shared by both stores
    │   ├── store.py           # CardStore interface + InMemoryCardStore (reference impl)
    │   ├── db.py              # Engine / session / table setup (dialect-agnostic)
    │   ├── orm.py             # SQLAlchemy CardRow model
    │   ├── sqlalchemy_store.py # SqlAlchemyCardStore — the default store
    │   └── seed.py            # Seed cards + seed_if_empty (mirrors the frontend's set)
    └── tests/                 # pytest suite (written test-first, run against both stores)
```

## Installation

**Frontend** (needs Node.js):

```bash
cd frontend
npm install
```

**Backend** (needs [`uv`](https://docs.astral.sh/uv/) — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`):

```bash
cd backend
uv sync          # creates .venv and installs FastAPI + dev tools
```

## Running the App

The app needs **both** servers running: the FastAPI backend and the Vite dev
server. The frontend calls a relative `/api/*` path; Vite proxies that to the
backend (`vite.config.js`), so the browser only ever makes same-origin requests
and there is no CORS to configure.

### 1. Backend (start this first)

```bash
cd backend
uv run uvicorn app.main:app --reload                      # http://localhost:8000
# or, to reach it directly on the machine's IP:
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Interactive API docs: **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**
- The API is served under `/api` (e.g. `GET /api/cards`); the full contract is in [`openapi.yaml`](./openapi.yaml).
- On first run the database (`backend/card_catalog.db`) is created and seeded with four sample cards. After that your data persists across restarts. Delete the file to start fresh.

### 2. Frontend

```bash
cd frontend
npm run dev        # http://localhost:5173 (also binds 0.0.0.0, so the IP works too)
```

If the backend is not on `http://localhost:8000`, copy `frontend/.env.example`
to `frontend/.env` and set `VITE_BACKEND_URL`. Restart the dev server after
changing `vite.config.js` or `.env` — Vite only reads them at startup.

## Database

Persistence goes through the `CardStore` interface (`backend/app/store.py`).
Two implementations exist:

| Store | Where | Used by |
|-------|-------|---------|
| `InMemoryCardStore` | `app/store.py` | reference implementation; tests; injectable into `create_app()` |
| `SqlAlchemyCardStore` | `app/sqlalchemy_store.py` | **the default** — what the server runs |

The SQLAlchemy store reads a single `DATABASE_URL` and nothing else is
dialect-specific, so:

```bash
# default (dev)
uv run uvicorn app.main:app                    # sqlite:///./card_catalog.db

# point at PostgreSQL later — no application code changes
uv add "psycopg[binary]"
DATABASE_URL="postgresql+psycopg://user:pass@localhost/card_catalog" uv run uvicorn app.main:app
```

Tables are created automatically on startup (`Base.metadata.create_all`); there
is no migration tool yet (Alembic would be the next step if the schema starts
changing). The board's column/position rules live in one place —
`app/board.py` — which both stores call, so they can't drift apart.

## Running Tests

**Backend** — the endpoints were built test-first (see [`_docs/specs.md`](./_docs/specs.md) §8):

```bash
cd backend
uv run pytest
```

- `tests/test_cards.py` — create/read/update/delete/move behaviour and validation. **Parametrized over both stores**, so every case runs against the in-memory store *and* a throwaway in-memory SQLite database; if they ever disagree, the suite fails.
- `tests/test_persistence.py` — data survives a fresh store on the same file; seeding only happens once.
- `tests/test_openapi.py` — `openapi.yaml` and the live app expose exactly the same set of operations.

**Frontend** — interactivity is manually verified against the spec at each stage; no automated suite yet.

## Challenges & Notes

Notes on anything non-obvious encountered while building this project, kept up to date as work progresses:

- **Git lives one level up.** This project's `.git` repository and `.gitignore` live in the parent directory (`/var/www/terzotech.net/ai-dev-tools/`), not in this folder. All git operations (status, add, commit, push) for this project are run from, or relative to, that parent directory rather than from `02-ai-assisted-full-stack-app/` itself.
- **AGENTS.md takes precedence over the published homework instructions** where the two differ (for example, the homework assumes `.gitignore`/`.git` live inside the project folder — here they live in the parent repo instead).
- **Spec-first workflow.** Before any code was written, the product specification was developed interactively (feature scope, data model, interaction choices, and the app name "Card Catalog" were all decided through a Q&A session) and captured in `_docs/specs.md`, per the course's spec-first methodology.
- **Mocked backend is one module, by design.** `frontend/src/api/cards.js` is the single seam between the UI and "the backend." Every function returns a `Promise` and mirrors what a real REST call will look like, so stage 4 (connecting to FastAPI) should only require rewriting that one file, not the components that call it.
- **Stage 4 held that line — mostly.** Swapping `cards.js` from `localStorage` to `fetch` needed no component changes: the mock had deliberately used the same field names (`due_date`, `column`, …) and return shapes as the API. The only other edits were additive: a `/api` proxy in `vite.config.js`, and wrapping the create/update/delete/move handlers in `App.jsx` (plus `CardEditor`'s submit) in `try/catch` so a backend error now shows in the board's error banner instead of becoming an unhandled promise rejection.
- **Vite proxy instead of CORS.** The frontend calls a relative `/api/*` path and the Vite dev server proxies it to the backend. This keeps every browser request same-origin regardless of whether the app is opened on `localhost` or the server IP, so no CORS config is load-bearing (the backend still sends permissive CORS headers as a fallback). Trade-off: the dev server must be restarted to pick up `vite.config.js` / `.env` changes.
- **dnd-kit's `useSortable` spreads `role="button"` onto the draggable element.** This meant a naive "click the element containing this text" test helper matched the outer card instead of the inner clickable content during manual browser verification. Not an app bug, but worth knowing if you write UI tests against these cards — target `.card-content` specifically, not the card root.
- **`crypto.randomUUID()` needs a secure context.** The mock backend seeded card IDs with `crypto.randomUUID()`, which the browser only exposes over HTTPS or on `localhost`. Serving the dev app from a bare server IP over plain HTTP (`http://<ip>:5173`) left `crypto.randomUUID` undefined, so seeding threw and — because the initial `getCards()` call had no `.catch()` — the app hung forever on "Loading Card Catalog…". Fixed by giving `uuid()` a `crypto.getRandomValues` fallback and adding `.catch()`/`.finally()` to the load call so failures surface as an error banner instead of an infinite spinner.
- **`uv` had to be installed for stage 3.** The spec mandates `uv` for the Python backend but it wasn't on the box; installed via `curl -LsSf https://astral.sh/uv/install.sh | sh` (lands in `~/.local/bin`). The backend is a non-packaged uv project (no `[build-system]` in `pyproject.toml`), so `uv sync` just builds a `.venv`; `pythonpath = ["."]` in the pytest config makes `import app` work without an editable install.
- **`move` returns the whole board, not one card.** Reordering shifts the `position` of every card it passes, so `POST /api/cards/{id}/move` responds with the full re-sequenced list (matching the frontend mock's `moveCard`). The plain `PATCH` endpoint deliberately rejects a `column` field (`extra="forbid"`) to keep "edit fields" and "move" as separate operations.
- **Starlette's `TestClient` prints an httpx deprecation warning.** Recent Starlette nudges toward an `httpx2` package that isn't released yet; the warning is cosmetic and the tests pass. Left as-is rather than pinning older Starlette.
- **Stage 5 was a store swap, not a rewrite.** `main.py` and the routes didn't change: `create_app()` just defaults to `SqlAlchemyCardStore` instead of the in-memory one. The refactor was pulling the column/position logic out of `InMemoryCardStore` into `app/board.py` (pure functions returning `Placement` values) so both stores share it — and the 28 existing tests, now parametrized to run against both, proved the behaviour matched.
- **In-memory SQLite needs a `StaticPool`.** `sqlite://` gives each connection its own private database, so `sessionmaker` opening a second connection would see no tables. `make_engine` pins one connection (`poolclass=StaticPool`) for in-memory URLs — used by the parametrized test fixture. File-backed SQLite doesn't have this problem.
- **Store construction had to be lazy.** `app/main.py` ends with `app = create_app()` for uvicorn, and `create_app()` used to build the store eagerly — which meant merely importing `app.main` in a test created and seeded `card_catalog.db` in the working directory. Fixed by building the default store on first request / server startup (FastAPI `lifespan`), not at import.
- **Reserved-word column names.** `column` and `position` are reserved (or function names) in the SQL standard / PostgreSQL. The ORM maps the attributes to physical columns `board_column` and `sort_position` to stay portable; the API field names are unchanged. `priority`/`column` are stored as plain `VARCHAR` (not a DB `ENUM`) and validated by Pydantic on the way out — again for portability.
- **SQLite drops timezones.** Stored `datetime`s come back naive; `_aware()` in the SQLAlchemy store re-stamps them as UTC so the API keeps emitting `...Z` timestamps consistently with the in-memory store.

## Course Context

Built for [Homework 2: Build and Ship an AI-Assisted Full-Stack App](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/cohorts/2026/02-development/homework.md) of the AI Dev Tools Zoomcamp.
