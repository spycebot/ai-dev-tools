# Card Catalog

A mini Kanban board for tracking personal tasks across three stages — **To Do**, **In Progress**, and **Done** — styled after the ["living paper"](https://shannonware.com) design language: an old computer-manual look built from index cards on aged paper.

This is homework assignment 3 for the [AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp) course: testing, containerizing, and deploying the app built in homework 2. The entire application — spec, frontend, backend, database, and now deployment infrastructure — is being built end-to-end with an AI coding agent (Claude Code), in stepwise fashion, with a commit + push after each completed step.

The full product specification lives at [`_docs/specs.md`](./_docs/specs.md) — §1–9 cover the app itself (carried over from homework 2), §10–11 cover the homework 3 deployment architecture. Read that document for complete functional requirements, the data model, and deployment design details — this README focuses on what the app is, how it's built, and how to run it.

## Status

**Homework 2 (app build) — all five stages complete:** spec → frontend prototype → backend (FastAPI, mock store) → connected frontend/backend → SQLite via SQLAlchemy. The app is a working full stack: a React board → a FastAPI service → a SQLAlchemy-backed SQLite database. **Both servers must be running locally** (see [Running the App](#running-the-app)).

**Homework 3 (test, containerize, deploy) — in progress:**

- [x] **1. Deployment spec** — target platform (AWS: ECS Fargate, RDS Postgres, ECR, GitHub Actions OIDC), environments, secrets, migrations, and CI/CD strategy decided; see [`_docs/specs.md`](./_docs/specs.md) §10–11
- [x] **2. Integration tests** — `backend/tests/integration/` against a real, ephemeral Postgres database (schema via Alembic); see [`docs/testing.md`](./docs/testing.md)
- [ ] **3. Containerization** — multi-stage `Dockerfile`, `docker-compose.yml`, SQLite → Postgres
- [ ] **4. Continuous integration** — `.github/workflows/ci.yml`
- [ ] **5. Deployment** — ECS Fargate + RDS Postgres + ECR, public URL
- [ ] **6. Continuous delivery** — `.github/workflows/deploy.yml`, staging/production, smoke tests, rollback

## Feature Summary

- Single user, gated by one shared password (see [Authentication](#authentication) below), one board, three fixed columns (no custom columns).
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
| Database (dev)    | SQLite                                             | Accessed through SQLAlchemy so the backend stays database-agnostic. `Base.metadata.create_all` builds the schema — dev/test convenience only. |
| Database (production target) | PostgreSQL (AWS RDS)                   | Schema built by **Alembic** migrations (`backend/migrations/`), not `create_all` — see [`_docs/specs.md`](./_docs/specs.md) §10. |
| Styling           | Custom CSS ("living paper" theme)                 | Special Elite (body) and Share Tech Mono (data/labels) fonts, aged-paper CSS background, blueprint blue (`#18385a`) and annotation amber (`#7a5c0a`) accent colors. |
| Authentication    | Single shared password, `bcrypt` + signed session cookie | No user table — one owner, one password. See [Authentication](#authentication). |
| Testing (integration) | `pytest-postgresql`                            | Real Postgres, ephemeral per-session cluster — no Docker. See [`docs/testing.md`](./docs/testing.md). |

## Project Structure

```
03-test-containerize-and-deploy-an-ai-assisted-app/
├── AGENTS.md          # Instructions for the AI coding agent building this project
├── README.md          # This file
├── openapi.yaml       # REST contract between frontend and backend (source of truth)
├── _docs/
│   └── specs.md       # Full product specification (app in §1-9, deployment in §10-11)
├── docs/               # Homework 3 deliverables
│   └── testing.md      # Test suite structure + why Postgres is provisioned the way it is
├── frontend/          # React + Vite app
│   ├── vite.config.js        # Dev server + /api → backend proxy
│   ├── .env.example          # VITE_BACKEND_URL (proxy target) override
│   └── src/
│       ├── api/cards.js       # The only module that talks to the backend (fetch)
│       ├── api/auth.js        # login / logout / getSession
│       ├── components/        # Column, CardItem, CardEditor, Login
│       ├── App.jsx            # Board state, auth state, drag-and-drop wiring
│       ├── App.css            # "Living paper" theme (layout + components)
│       └── index.css          # Aged-paper background, fonts, color tokens
└── backend/           # FastAPI app (uv-managed)
    ├── pyproject.toml         # Dependencies + pytest config
    ├── .env.example           # AUTH_*, CORS_ORIGINS — copy to .env
    ├── card_catalog.db        # Dev SQLite database (git-ignored, created on first run)
    ├── alembic.ini             # Alembic config (URL resolved at runtime, not hardcoded)
    ├── migrations/              # Alembic migrations — the Postgres schema source of truth
    │   ├── env.py               # Points at app.db.Base.metadata + DATABASE_URL
    │   └── versions/             # e.g. create_cards_table
    ├── scripts/
    │   └── set_password.py    # Generate/rotate the shared password's bcrypt hash
    ├── app/
    │   ├── main.py            # FastAPI app + routes (create_app factory)
    │   ├── auth.py             # Password check, session cookies, rate limiting
    │   ├── models.py          # Pydantic schemas (Card, CardCreate, CardUpdate, CardMove)
    │   ├── board.py           # Pure column/position rules, shared by both stores
    │   ├── store.py           # CardStore interface + InMemoryCardStore (reference impl)
    │   ├── db.py              # Engine / session / table setup (dialect-agnostic)
    │   ├── orm.py             # SQLAlchemy CardRow model
    │   ├── sqlalchemy_store.py # SqlAlchemyCardStore — the default store
    │   └── seed.py            # Seed cards + seed_if_empty (mirrors the frontend's set)
    └── tests/                 # pytest suite (written test-first, run against both stores)
        └── integration/        # Real-Postgres suite — migrations, auth, card workflows
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

The backend won't start without a password configured — see
[Authentication](#authentication) below before running it for the first time.

## Authentication

The app is gated by **one shared password** — there are no user accounts,
sign-up, or "forgot password" flow, because there's only ever one account
(you). The password's `bcrypt` hash lives in an environment variable, never
in the database or in source; a signed, `httpOnly` session cookie (30-day
lifetime) keeps you logged in after that. Set it up once:

```bash
cd backend
cp .env.example .env
uv run python scripts/set_password.py    # prompts for a password, prints two lines
# paste the printed AUTH_PASSWORD_HASH and AUTH_SECRET_KEY into backend/.env
```

The server refuses to start until `AUTH_PASSWORD_HASH` and `AUTH_SECRET_KEY`
are both set (see `backend/.env.example` for the full list of variables). To
change the password later, just run the script again and update `.env` —
there's no in-app reset flow by design; you're the only user, so rotating the
password is a config edit, not a feature to build and maintain.

A handful of failed login attempts from the same IP triggers a short
lockout (see `app/auth.py`), to slow down anyone guessing at the password.

## Running the App

The app needs **both** servers running: the FastAPI backend and the Vite dev
server. The frontend calls a relative `/api/*` path; Vite proxies that to the
backend (`vite.config.js`), so the browser only ever makes same-origin requests
and there is no CORS to configure — which also means the session cookie just
works, with no cross-origin cookie configuration needed.

### 1. Backend (start this first)

```bash
cd backend
uv run uvicorn app.main:app --reload                      # http://localhost:8000
# or, to reach it directly on the machine's IP:
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open the app and you'll land on a password screen first — log in with the
password you set above.

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

**Backend** — the endpoints were built test-first (see [`_docs/specs.md`](./_docs/specs.md) §8). Full detail, including how the integration suite provisions Postgres, is in [`docs/testing.md`](./docs/testing.md):

```bash
cd backend
uv run pytest                        # everything — 85 tests, ~8s, no setup required
uv run pytest -m "not integration"   # unit/store tests only
uv run pytest -m integration         # integration tests only
```

- `tests/test_cards.py` — create/read/update/delete/move behaviour and validation. **Parametrized over both stores**, so every case runs against the in-memory store *and* a throwaway in-memory SQLite database; if they ever disagree, the suite fails.
- `tests/test_persistence.py` — data survives a fresh store on the same file; seeding only happens once.
- `tests/test_openapi.py` — `openapi.yaml` and the live app expose exactly the same set of operations.
- `tests/test_auth.py` — login/logout/session, cookie tampering, and rate limiting. Card tests log in with a fixed test password (see `conftest.py`); these tests exercise the logged-out state directly.
- `tests/integration/` — the same kinds of workflows (migrations, auth, card CRUD/move) but against a **real, ephemeral PostgreSQL cluster** with the schema built by Alembic, not SQLite. See [`docs/testing.md`](./docs/testing.md) for how that database is provisioned without Docker and without touching this machine's other databases.

**Frontend** — interactivity is manually verified against the spec at each stage; no automated suite yet.

## Challenges & Notes

Notes on anything non-obvious encountered while building this project, kept up to date as work progresses:

- **Requirements discussion: Docker on a shared production box, for integration testing.** This machine already runs a system PostgreSQL 17 service that hosts another live site's database (`shannonware`), and has no Docker installed. The natural options were: install Docker and use `testcontainers`; add a dedicated role/database to the existing system Postgres service; or provision a fully separate, ephemeral Postgres cluster per test session. Docker was ruled out first — a root-privileged daemon is a meaningful addition to the attack surface of a box serving other live sites, for a benefit (container parity with CI) not actually needed yet at the testing stage. Between the two native-Postgres options, a dedicated role on the *existing* service was rejected too, in favor of **`pytest-postgresql`**, which boots a throwaway Postgres cluster (its own data directory, port, and process, via the `initdb`/`postgres` binaries the `postgresql-17` apt package already installs) per test session and tears it down after — this removes even the possibility of a test misconfiguration touching real data, since it's never the same server process. See [`docs/testing.md`](./docs/testing.md) for the full writeup. (Docker itself will be needed later, in Step 3, to build and test the app's own container images — that's a separate decision, likely to land on "build/test in CI, not on this box.")
- **`alembic init` directory naming pitfall.** The default `alembic init alembic` command names the migrations directory `alembic/` — which, combined with this project's `pythonpath = ["."]` pytest setting (and `backend/` generally being on `sys.path` when Alembic itself runs from that directory), risks the local directory shadowing the *installed* `alembic` package on `import alembic`. Used `alembic init migrations` instead (directory named `migrations/`, referenced by `script_location` in `alembic.ini`) to sidestep the collision entirely.
- **`pytest-postgresql`'s default `dbname` is never actually created by `postgresql_proc` alone.** The fixture's default database name (`tests`) is only created on demand by the separate `postgresql` fixture (which hands back a ready connection to it); a handwritten admin connection built from `postgresql_proc`'s host/port/dbname to issue `CREATE DATABASE` therefore failed with `database "tests" does not exist`. Fixed by always connecting to the cluster's always-present `postgres` bootstrap database to run `CREATE DATABASE`/`DROP DATABASE`, the same way you would against any real Postgres cluster.
- **Requirements discussion: AWS vs. a PaaS wrapper (Render/Fly.io/Railway) for deployment.** The course video/article deploy to AWS. Render, Fly.io, and Railway are themselves built on top of AWS/GCP, so choosing one of them is mainly a convenience trade — automatic TLS, managed Postgres backups, and zero-downtime deploys come out of the box, at the cost of hiding the underlying primitives (VPC, IAM, ALB, ECS task definitions) behind another vendor's control plane. Since one of the explicit goals here is building toward an AWS certification, that hidden complexity is exactly the job-relevant skill worth practicing rather than avoiding. Decision: deploy on AWS directly — **ECS Fargate** for the containers, **RDS Postgres** as the managed database, **ECR** for container images, and **GitHub Actions with OIDC** to assume an AWS IAM role for CI/CD (no long-lived AWS access keys stored as GitHub secrets). See [`_docs/specs.md`](./_docs/specs.md) §10 for the full deployment spec.
- **Requirements discussion: staging environment cost vs. the homework's explicit requirement.** A single-production-environment setup was considered first, to minimize AWS cost/complexity for a solo learning project — but the homework explicitly lists staging vs. production as a required deliverable, so that tradeoff would likely cost points. Decision: a **lightweight staging setup** — one RDS instance hosting two databases (`staging_db`, `prod_db`) and one ECS cluster running two low-cost Fargate services, rather than fully duplicated infrastructure. `deploy.yml` promotes a build through staging (migrate → deploy → smoke test) before repeating the same sequence against production, with rollback to the last known-good image tag on smoke test failure.
- **Requirements discussion: one container vs. two.** Rather than separate frontend/backend ECS services behind path-based ALB routing, the backend's Docker image serves the built frontend directly (FastAPI mounts the Vite build output), keeping the current dev setup's same-origin, no-CORS design and halving the AWS footprint (one ALB target group, one ECS service per environment instead of two).
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
- **Auth added after all five build stages, ahead of public hosting.** With one owner and no user accounts, a full auth system (user table, hashed-password DB rows, email-based reset) would be solving a problem this app doesn't have. Went with the smallest thing that meets the actual goals (stop drive-by defacement/probing, let the owner still use it as a real kanban, let it be shown to prospective employers): one password, its `bcrypt` hash in an env var (not the database, not source), a signed timed cookie for sessions, and a `scripts/set_password.py` CLI instead of a self-service reset flow. `create_app()` takes an injectable `AuthConfig`, mirroring how it already took an injectable `CardStore` — tests use a fixed low-cost test password instead of touching real environment variables.
- **`create_app()`'s auth config had to be lazy, same as the store.** Resolving `AuthConfig` from the environment eagerly inside `create_app()` meant `from app.main import create_app` (which `conftest.py` does) crashed at import time — before any test could inject its own config — whenever `AUTH_PASSWORD_HASH`/`AUTH_SECRET_KEY` weren't set. Fixed by building it on first use via the same holder-dict pattern as `get_store()`, with `lifespan` still resolving it eagerly at real server startup so a genuine deployment fails fast on missing config rather than on the first request.

## Course Context

Built for [Homework 2: Build and Ship an AI-Assisted Full-Stack App](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/cohorts/2026/02-development/homework.md) of the AI Dev Tools Zoomcamp.
