# Testing

The backend test suite (`backend/tests/`) has two layers: fast unit/store
tests that need nothing beyond Python, and an integration suite that
exercises a real PostgreSQL database.

## Running the tests

```bash
cd backend
uv run pytest                        # everything (unit + integration)
uv run pytest -m "not integration"   # unit/store tests only — no Postgres needed
uv run pytest -m integration         # integration tests only
```

The full suite is 85 tests and runs in well under 10 seconds locally,
including the Postgres cluster boot — fast enough to run on every push, per
the homework requirement.

## Unit / store tests (`backend/tests/*.py`, not `tests/integration/`)

Card CRUD, board rules (`app/board.py`), auth (login/logout/session/rate
limiting), persistence, and the `openapi.yaml` contract. Every card/board
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

## CI

`.github/workflows/ci.yml` (Step 3 of this homework, not yet built) will run
both layers on every push/PR as merge gates. The unit tests need no special
CI setup; the integration tests can either keep using `pytest-postgresql`
(as here — it needs no Docker, and GitHub-hosted runners ship the
`postgresql` apt package) or use GitHub Actions' built-in `services:
postgres:` container — a decision left for that step.
