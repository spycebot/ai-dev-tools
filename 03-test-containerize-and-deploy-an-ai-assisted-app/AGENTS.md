# Agent Capabilities Quick Reference

Portable instructions for any coding agent (Claude Code, Codex, or
equivalent) working in this repo — added as part of the Module 5 "Agent
Extension Pack" (`../05-agent-capabilities/`). The homework-process notes
below this section are specific to how this app was originally built;
this section is the durable reference for working in it going forward.

**Architecture**: React + Vite frontend (`frontend/`) talking to a FastAPI
backend (`backend/`) over `/api/*`, proxied same-origin by Vite in dev (no
CORS to configure). Persistence goes through the `CardStore` interface
(`backend/app/store.py`); `SqlAlchemyCardStore` is the default, backed by
SQLite in dev and Postgres in production via one `DATABASE_URL`. Board
column/position rules live once in `backend/app/board.py`, shared by every
store. Auth is a single shared password (`backend/app/auth.py`): bcrypt
hash + signed session cookie, no user table. Full detail: `README.md`,
`_docs/specs.md`.

**Commands**:
```bash
cd backend && uv run uvicorn app.main:app --reload   # backend, :8000
cd frontend && npm run dev                           # frontend, :5173
cd backend && uv run pytest                           # full suite (~85 tests)
cd backend && uv run pytest -m "not integration"      # unit/store only, no Postgres
cd backend && uv run pytest -m integration            # integration only (needs postgresql-17's initdb/postgres on PATH)
cd frontend && npm run lint                           # oxlint
```

**Conventions**: `create_app(store=None, auth_config=None)` takes injectable
dependencies for testing; both the store and auth config resolve lazily
(importing `app.main` must never touch disk or require env vars — see
README "Challenges & Notes"). ORM columns `column`/`position` are reserved
words, mapped to `board_column`/`sort_position` physically while the API
keeps the original field names. Card/board tests are parametrized over both
`CardStore` implementations — if they disagree, the suite fails by design.

**Security boundaries**: `AUTH_PASSWORD_HASH` and `AUTH_SECRET_KEY` live only
in `backend/.env` (git-ignored), never in source or the database — the
server refuses to start without them. Never print, log, or commit `.env`
contents, `card_catalog.db`, or a real session cookie value. The MCP server
and subagent in `../05-agent-capabilities/` are read-only / test-only by
design — see `../05-agent-capabilities/docs/permissions.md` before granting
either more than that.

-----

The work for this project is done in the directory /var/www/terzotech.net/ai-dev-tools/03-test-containerize-and-deploy-an-ai-assisted-app . The Git information is located in the parent directory, at /var/www/terzotech.net/ai-dev-tools/ . 

For homework assignment 3 of the AI Dev Tools course, we containerise and deploy the mini Kanban board (also referred to as 'this software project'). This is an end-to-end application built with an AI agent that includes a Node.js frontend, a Python backend, and a database. The database used in development will be SQLite. We must be able to switch to PostgreSQL in production.

Homework details: https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/03-deployment/01-test-containerize-and-deploy-an-ai-assisted-app.md

-----

The specification for this software project will be developed in an interactive TUI session. Please save the completed specification to `_docs/specs.md` . 

The homework details are found at ai-dev-tools-zoomcamp/cohorts/2026/02-development/homework.md at main · DataTalksClub/ai-dev-tools-zoomcamp · GitHub , which was updated on 09 September 2026 around 14:30. However, instructions in this AGENTS.md fill will take precidence. For example, the .gitignore file and .git folder are in the parent directory, not in this directory.

** IMPORTANT ** This application will be developed in a stepwise fashion, not all at once. Please commit changed and modified files to the repository, the push to the remote repository (GitHub.com), after each completed step. The main steps are as follows:

1. Integration tests (`tests/integration/`) — exercise a real database, cover migrations, authentication, and frontend-to-backend workflows, fast enough to run on every push
2. Containerization — multi-stage `Dockerfile` and `docker-compose.yml`, swapping SQLite for Postgres
3. Continuous integration — `.github/workflows/ci.yml` (lint, unit tests, integration tests as merge gates)
4. Deployment — public URL (Render, Fly.io, Railway, or Cloud Run), managed database, automatic migrations
5. Continuous delivery — `.github/workflows/deploy.yml`, staging vs. production environments, post-deploy smoke tests, documented rollback procedures

Expected deliverables by the end of this assignment: `tests/integration/`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`, `docs/testing.md`, `docs/deployment.md`, `docs/release-process.md`. The app must be reproducible locally from the README.

-----

** Additional Instructions **
1. Continue to maintain the README.md file, 
2. The README.md file should be verbose, as well as include the tech stack, installation instructions, and operation instructions.
3. Continue to make note of challenges encountered in the README.md file


