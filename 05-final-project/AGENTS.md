# Card Catalog: instructions for coding agents

Portable instructions for any coding agent (Claude Code, Codex, or
equivalent) working on Card Catalog, the AI Dev Tools Zoomcamp final
project. Agent tooling: `mcp-server/`, `plugins/`, `.claude/` (map in
`docs/agent-extension-pack.md`).

**Architecture**: React + Vite frontend (`frontend/`) talking to a FastAPI
backend (`backend/`) over `/api/*`, proxied same-origin by Vite in dev (no
CORS to configure). Persistence goes through the `CardStore` interface
(`backend/app/store.py`); `SqlAlchemyCardStore` is the default, backed by
SQLite in dev and Postgres in production via one `DATABASE_URL`. Board
column/position rules live once in `backend/app/board.py`, shared by every
store. Auth is a single shared password (`backend/app/auth.py`): bcrypt
hash + signed session cookie, no user table. Full detail: `README.md`,
`_docs/specs.md`.

**Commands** (`make help` lists them all):
```bash
make up                                              # whole stack in Docker on Postgres, :8000
make test                                            # every test in Docker (backend unit + integration, frontend, lint)
cd backend && uv run uvicorn app.main:app --reload   # backend, :8000
cd frontend && npm run dev                           # frontend, :5173
cd backend && uv run pytest                           # full backend suite (103 tests)
cd backend && uv run pytest -m "not integration"      # unit/store only, no Postgres
cd backend && uv run pytest -m integration            # integration only (needs postgresql-17's initdb/postgres on PATH)
cd frontend && npm run lint                           # oxlint
cd frontend && npm test                               # Vitest + Testing Library (jsdom, fetch stubbed)
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
and subagent in `mcp-server/` and `.claude/agents/` are read-only / test-only by
design — see `docs/permissions.md` before granting
either more than that.

**Team and process**: who does what (owner, builder, `api-reviewer`
subagent, MCP ops tools, incident responder) and how work passes between
them is in `docs/agent-team.md`. Work is tracked in GitHub Issues
(https://github.com/spycebot/ai-dev-tools/issues):

- Start from an issue. If there isn't one, create it (`gh issue create`)
  with a goal and acceptance criteria as a checklist, and confirm the scope
  with the owner before writing code.
- Read it first: `gh issue view <n>`.
- One branch per issue. The PR description says `Closes #<n>` and states
  how each acceptance criterion was checked; merging closes the issue.
- Follow-ups found along the way become new issues, not scope creep.

**Project docs** (read the one that matches the task; don't load them all):

| Topic | File |
|---|---|
| Product spec: scope, data model, requirements, deployment design | `_docs/specs.md` |
| API contract (source of truth) | `openapi.yaml` |
| Agent team, roles and hand-offs | `docs/agent-team.md` |
| How the agent was directed, and its past mistakes | `docs/ai-workflow.md` |
| What each agent tool may do | `docs/permissions.md` |
| Tests and CI | `docs/testing.md` |
| AWS architecture and server operations | `docs/deployment.md` |
| Release process, production approval, rollback | `docs/release-process.md` |
| Monitoring, alert, incident responder, incidents | `observability/README.md`, `incident-response/README.md`, `docs/operations-and-security-report.md` |
| Security audits and finding dispositions | `security-audit/audit-brief.md` |

**Working rules** (from the owner):

- Git lives one level up: the repository root is `../` (`ai-dev-tools`);
  this app is the `05-final-project/` folder. Workflows are in
  `../.github/workflows/`.
- Work in small steps. Commit and push after each completed step, on a
  branch, through a pull request. `main` is protected; only the owner merges.
- Keep `README.md` current and verbose: tech stack, installation and
  operating instructions. Record anything non-obvious you run into under
  README *Challenges & Notes*.
- These instructions take precedence over the course's published homework
  pages where the two differ.
