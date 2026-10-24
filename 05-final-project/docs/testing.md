# Testing

The backend test suite (`backend/tests/`) has two layers: fast unit/store
tests that need nothing beyond Python, and an integration suite that
exercises a real PostgreSQL database. The frontend has its own Vitest suite
(`frontend/src/**/*.test.*`); see [Frontend tests](#frontend-tests).

## Running the tests

One command runs everything, with nothing but Docker on the host:

```bash
make test     # backend unit + integration, frontend tests, lint
```

It builds the two stages of [`Dockerfile.test`](../Dockerfile.test):
`backend-test` (the backend's locked dependencies plus Debian's
`postgresql-17`, so the integration suite boots its throwaway cluster
inside the container) and `frontend-test` (`npm ci`, then `npm test` and
`npm run lint`). Both use the same digest-pinned base images as the app.
CI runs the same commands natively instead (see [CI](#ci)).

Natively (`make test-local` runs the backend and frontend suites in turn):

```bash
cd backend
uv run pytest                        # everything (unit + integration)
uv run pytest -m "not integration"   # unit/store tests only — no Postgres needed
uv run pytest -m integration         # integration tests only
```

The backend suite is 98 tests (89 unit, 9 integration) and runs in about 10 seconds locally,
including the Postgres cluster boot — fast enough to run on every push, per
the homework requirement.

## Unit / store tests (`backend/tests/*.py`, not `tests/integration/`)

Card CRUD, board rules (`app/board.py`), auth (login/logout/session/rate
limiting), persistence, the `openapi.yaml` contract, the telemetry the 5xx
alert depends on (and that no card content or credentials reach it), the
`.env` writer behind `make up`, and the staging write smoke test (`scripts/smoke_write.py`). Every card/board
test is **parametrized over both `CardStore` implementations** —
`InMemoryCardStore` and `SqlAlchemyCardStore` on a throwaway in-memory
SQLite database — so if the two stores ever disagree on behavior, the suite
fails. No external services required; these are what a plain `uv run pytest`
with zero setup should always be able to run.

## Integration tests (`backend/tests/integration/`)

These exercise the actual production stack end-to-end: a **real PostgreSQL
database**, schema built by **Alembic migrations** (not
`Base.metadata.create_all`, which is a SQLite/dev-only shortcut), the real
`SqlAlchemyCardStore`, authentication, and full API workflows shaped like
what the frontend actually does (create → edit → move/reorder → delete).

| File | Covers |
|---|---|
| `test_migrations.py` | `alembic upgrade head` creates the expected schema; `downgrade` to base drops it cleanly; upgrading twice is a safe no-op (every real deploy runs it, changed schema or not) |
| `test_auth_workflow.py` | Login gating, logout, and that a session cookie is still valid against a *fresh* database connection — standing in for a backend restart against the same RDS instance |
| `test_card_workflow.py` | Full create/edit/move/delete round trips, within-column reordering, and that data outlives the process (a second connection to the same database sees what the first wrote) |

Auth and card-field edge cases (validation, 404s, rate limiting, forged
cookies, etc.) are **not** re-tested here — they're store-independent by
construction and already covered exhaustively by the parametrized unit
suite. Integration tests exist to prove the pieces that only show up with a
*real*, separately-provisioned database: the Alembic-managed schema, and the
stack wired together end-to-end.

### How the database is provisioned — and why

No Docker is used, and these tests **never touch this machine's system
PostgreSQL service** (the one that also hosts other production databases on
this box). Instead, `tests/integration/conftest.py` uses
[`pytest-postgresql`](https://pypi.org/project/pytest-postgresql/) to start
a completely separate, ephemeral Postgres *cluster* — its own data
directory (under a pytest temp dir), its own port, its own `postgres`
process — using the `initdb`/`postgres` binaries that ship with the
`postgresql-17` apt package. That cluster is torn down when the test session
ends. Each individual test then gets its own throwaway database
(`CREATE DATABASE`/`DROP DATABASE ... WITH (FORCE)`) on that ephemeral
cluster, so tests can't see each other's data either.

This was a deliberate choice, made after discussion, over two alternatives:

- **Docker + testcontainers** — rejected for local use on this box because
  it's a shared server hosting other live sites; installing a root-privileged
  Docker daemon there was judged to add more attack surface than the
  isolation was worth. (Docker itself is still needed later, in Step 3, to
  build and test the app's own container images — that's a separate
  decision to revisit then, likely scoped to CI rather than this machine.)
- **A dedicated role/database on the box's existing system Postgres
  service** — rejected in favor of the fully separate ephemeral cluster
  above, because that service already hosts another site's production
  database (`shannonware`) in the same cluster. A scratch cluster removes
  even the *possibility* of a test misconfiguration pointing at real data,
  at the cost of a ~1 second cluster boot per test session.

`pg_ctl` isn't on `PATH` on Debian/Ubuntu (multiple PostgreSQL major
versions can coexist), so its location is configurable via the
`PG_CTL_PATH` environment variable if it isn't at the Postgres 17 default
(`/usr/lib/postgresql/17/bin/pg_ctl`) — for example, on a CI runner with a
different bundled version.

## Frontend tests

```bash
cd frontend
npm test            # vitest run: 44 tests in jsdom, no backend needed
```

Components render in jsdom with React Testing Library and are driven with
`user-event`, the way a person would use them (labels, roles, button names),
not by CSS class or component internals. `fetch` is replaced per test by a
small stub (`src/test/fetch.js`) that answers `"METHOD /path"` routes and
records every request, so tests assert on what the app *sent* as well as on
what it shows.

The drop logic was moved out of `App.jsx` into pure functions in
`src/board.js` (`groupByColumn`, `planMove`, `applyMove`) so it can be tested
without simulating pointer events, which dnd-kit's sensors need and jsdom
doesn't provide. Those tests found a real bug: a card dropped back onto its
own slot jumped to the bottom of its column.

## CI

[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) (at the
repository root — GitHub only reads workflows from there) runs on every push
to `main` and every pull request that touches this app, as five independent
jobs. All five are required status checks for merging to `main`:

| Job | Runs | Fails when |
|---|---|---|
| `lint` | `npm ci`, `npm run lint` (oxlint), `npm test` (Vitest), `npm run build` | a lint error, a frontend test fails, or the production frontend build breaks |
| `unit-tests` | `uv sync --frozen`, `pytest -m "not integration"` | any unit/store test fails, or `uv.lock` is out of date |
| `integration-tests` | installs PostgreSQL **17** from the PGDG apt repo, then `pytest -m integration` with `PG_CTL_PATH` pointed at it | any migration/auth/workflow test against real Postgres fails |
| `container` | builds the `Dockerfile` (layer cache in GitHub Actions), then `docker compose up --wait` on that image and a smoke test: `/health`, the frontend's `index.html`, a 401 without a session, a login, and an authenticated `GET /api/cards` | the image doesn't build, migrations fail, the app doesn't become healthy, or any smoke request fails |
| `security-scan` | Semgrep (`security-audit/run-semgrep.sh --error`) and pip-audit on the backend's locked runtime dependencies | a new Semgrep finding without a recorded `nosemgrep` decision, or a dependency with a known vulnerability (see [`security-audit/`](../security-audit/audit-brief.md)) |

The integration job keeps the same `pytest-postgresql` approach used locally
(no Docker, no `services:` container) and installs Postgres 17 rather than
using the runner's bundled version, so CI exercises the same major version
as production (RDS Postgres 17). The container smoke test generates a
throwaway password hash and secret key inside the job; no real secret is
used or stored in CI.

`deploy.yml` (Step 5) calls this same workflow (`workflow_call`) as its first
job, so nothing is deployed unless every check above passes on that commit.
