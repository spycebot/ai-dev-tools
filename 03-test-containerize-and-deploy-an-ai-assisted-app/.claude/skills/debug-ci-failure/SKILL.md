---
name: debug-ci-failure
description: Triage a failing Card Catalog backend test run (unit or integration) in this repo. Use when `uv run pytest` fails, or a GitHub Actions run fails, and the cause isn't immediately obvious from the first error line.
---

# Debug a Card Catalog test failure

A repeatable procedure for this repo, not a generic "fix the bug" prompt — it
encodes failure modes that have already bitten this codebase once (see
`README.md` → "Challenges & Notes") so they get checked before re-deriving
them from scratch.

## 1. Classify the failure

```bash
cd backend
uv run pytest -m "not integration" -q   # unit/store tests — no external services
uv run pytest -m integration -q         # integration tests — needs postgresql-17's initdb/postgres on PATH
```

- If only `-m integration` fails and `-m "not integration"` passes: the
  problem is in Postgres provisioning, Alembic migrations, or something that
  only diverges from SQLite under real Postgres (e.g. timezone handling,
  reserved-word columns). Read `docs/testing.md` first.
- If both fail, or `-m "not integration"` alone fails: it's an application
  logic bug, not an environment issue.

## 2. Check the known-gotcha list before debugging from scratch

Grep `README.md`'s "Challenges & Notes" section for the failing area —
several non-obvious bugs here have already been found and fixed once:

```bash
grep -n -A2 -i "static\|lazy\|reserved\|timezone\|dbname\|alembic init" ../README.md
```

Common recurring causes in this repo:
- **Store disagreement**: card/board tests are parametrized over
  `InMemoryCardStore` and `SqlAlchemyCardStore` (`backend/tests/test_cards.py`).
  A failure in only one parametrization means the two stores' behavior has
  drifted — check `app/board.py` (shared logic) vs. store-specific code.
- **Eager config resolution**: `create_app()` must stay lazy about building
  the store and `AuthConfig` (see `app/main.py` comments). A test failing
  only on import, before any test body runs, usually means something made
  env/DB access eager again.
- **Reserved SQL words**: `column` and `position` are reserved; the ORM maps
  them to `board_column`/`sort_position` (`app/orm.py`). A raw-SQL or Alembic
  change using the bare names will break against real Postgres even if
  SQLite tolerates it.
- **`pytest-postgresql` dbname**: admin connections for `CREATE DATABASE`
  must target the cluster's bootstrap `postgres` database, not
  `postgresql_proc`'s configured `dbname` (it isn't created automatically).

## 3. Reproduce the smallest failing case

```bash
uv run pytest path/to/test_file.py::test_name -q -x --tb=short
```

## 4. Check the contract, not just the code

If the failure involves a request/response shape, confirm `openapi.yaml`
and the live app still agree:

```bash
uv run pytest tests/test_openapi.py -q
```

## 5. Fix, then re-run the full suite

```bash
uv run pytest -q
```

Don't fix only the test that was reported failing — the parametrized suite
exists specifically to catch the same bug reappearing in the other store.
