# How AI was used to build Card Catalog

Card Catalog was built end to end with an AI coding agent, **Claude Code**
(Anthropic's Claude models), working in a terminal on the development server
(first a VPS, later the AWS EC2 host that also runs the app).
The developer set the goals, made the product and architecture decisions,
handled every credential and console change, and merged every pull request.
The agent wrote the spec drafts, code, tests, infrastructure and docs, and
explained its work at each step.

This document covers what context the agent was given, how work was split up,
how its output was reviewed and verified, and where it went wrong. Every claim
here can be checked in the Git history, the pull requests, or the README's
[Challenges & Notes](../README.md#challenges--notes).

## The roles

| | The developer | The agent |
|---|---|---|
| **Decides** | What to build and in what order; architecture trade-offs (AWS vs. a PaaS, EC2 + RDS vs. ECS, SSM vs. SSH); domain names; when a step is done | How to implement a decided step; which tests prove it; how to explain it |
| **Does** | Creates accounts, tokens and IAM roles in consoles; sets DNS; chooses the login password; merges pull requests | Writes code, tests, Dockerfiles, workflows, scripts and docs; runs tests and builds; opens pull requests; watches deploys and diagnoses failures |
| **Keeps out of the agent's hands** | Secret values, cloud-console and IAM changes, merges to `main` | Never sees a secret's plaintext; can't merge to `main` (branch protection plus Claude Code's safety checks) or change IAM (its server role isn't allowed to) |

## Context the agent works from

The agent has no memory of the project between sessions beyond what's written
down, so the project keeps its context in files:

| File | Role |
|---|---|
| [`AGENTS.md`](../AGENTS.md) (via [`CLAUDE.md`](../CLAUDE.md)) | The standing prompt. The bottom half is written by the developer: where the work happens, the homework's step list, "commit and push after each completed step", "AGENTS.md takes precedence over the published homework", README upkeep rules. The top half, a quick reference of architecture, commands, conventions and security boundaries, was added for any agent working in the repo later. |
| [`_docs/specs.md`](../_docs/specs.md) | The product spec: scope, data model, interactions, API, test plan, and the deployment design (§10–11). Every implementation step cites it. |
| [`openapi.yaml`](../openapi.yaml) | The API contract. `backend/tests/test_openapi.py` fails if the app and the contract drift. |
| [README Challenges & Notes](../README.md#challenges--notes) | A running log of surprises, wrong turns and the reasons behind decisions. It doubles as memory for the next session. |
| [`.claude/`](../.claude/), [`.mcp.json`](../.mcp.json) | Project-level agent tooling: a debugging skill, an API-review subagent, an MCP server for tests and lint, and a hook that blocks writes to secret files. See [`agent-extension-pack.md`](./agent-extension-pack.md). |
| Course pages | Each homework's instructions, given to the agent as links. |

## How the work was split up

The app was built in small, verifiable steps. Each step ended with a commit,
and from the deployment work onwards with a pull request.

| Phase | Step | What the developer asked for | How it was verified |
|---|---|---|---|
| Homework 2: build | 1. Spec | An interactive Q&A in the terminal to pin down scope, data model, interactions and the name "Card Catalog", saved to `_docs/specs.md` | Developer review of the spec before any code |
| | 2. Frontend prototype | The board UI against a mocked backend, isolated in one module (`src/api/cards.js`) | Manual check in the browser against the spec |
| | 3. Backend | FastAPI endpoints, **test-first**, with an in-memory store | pytest suite written before the endpoints |
| | 4. Connect | Swap the mock module for real `fetch` calls | No component changes needed: proof the seam held |
| | 5. Database | SQLAlchemy + SQLite behind the same store interface | The same tests, parametrized to run against both stores |
| | Auth | One shared password before going public (bcrypt hash + signed cookie) | Auth tests; developer chose the "smallest thing that works" design |
| Homework 3: ship | 1. Deployment spec | Target platform, environments, secrets, CI/CD design (`specs.md` §10–11) | Developer decision (later revised: see below) |
| | 2. Integration tests | A real, throwaway PostgreSQL per run, schema built by Alembic | Separate `integration` marker; runs in CI |
| | 3. Containers | Multi-stage Dockerfile; Compose with Postgres and a migrate job | Compose smoke test, also in CI |
| | 4. CI | Lint, unit, integration and container jobs as merge gates | Branch protection requires all four |
| | 5. Deploy | EC2 + RDS behind Caddy, two environments | Live HTTPS checks; isolation test between the staging and production databases |
| | 6. CD | Merge → build → staging → production through SSM with OIDC | Server-side and outside smoke tests; a deliberately broken image to prove the automatic rollback |
| Module 5 | Extension pack | Skill, subagent, MCP server, hook, plugin and permission notes | [Demo walkthrough](./agent-demo.md) |
| Final project | Consolidation | Move everything into `05-final-project/` | CI on the PR; the deploy after merge exercises every moved path |

**Prompting style.** The developer gave goals and constraints, not code: "Use
cards.terzotech.net and staging.cards.terzotech.net", "RDS free tier: yes",
"branch protection: required by the homework", "Merged PR #1, watch the
deploy". When a choice was the developer's to make (platform, where a cluster
should run, whether to start a new project), the agent laid out the options
with costs and a recommendation, and the developer chose. Long copy-paste
material such as IAM policies went into files on the server, not the chat.

## Review and verification

Nothing reaches production on the agent's word alone:

1. **Tests first where they're cheap.** Backend behaviour was specified as
   tests before the code. Board rules live in one pure module that both stores
   share, and the same tests run against both stores, so they can't quietly
   diverge.
2. **A contract test.** `test_openapi.py` keeps the hand-written `openapi.yaml`
   and the running app in sync.
3. **Real infrastructure in tests.** The integration suite runs on real
   PostgreSQL with real migrations, not SQLite.
4. **CI as a gate the agent can't skip.** `main` is protected: all four checks
   must pass and the branch must be up to date, and the rule applies to admins
   too.
5. **A human merge.** The agent opens pull requests; the developer merges. Once
   the agent tried to merge PR #1 itself, and Claude Code's safety checks
   blocked it, which is the intended outcome.
6. **Verification after deploy.** `deploy/smoke.sh` runs on the server and
   again from GitHub's runners. A failure rolls back automatically. The agent
   then checks the live URLs and reports the deployed image tag.
7. **Manual checks for the UI.** Frontend behaviour is checked in a browser
   against the spec at each stage. Automated frontend tests are on the
   final-project to-do list.

## Where the AI went wrong, and how it was caught

| What went wrong | Caught by | Fix |
|---|---|---|
| The app hung on "Loading…" when served over plain HTTP from an IP address: `crypto.randomUUID()` needs a secure context, and the error was swallowed | Manual browser check | Fallback ID generator, and load errors now show in the UI |
| Importing `app.main` in a test created a database file, then crashed without auth env vars: the store and auth config were built eagerly at import | Tests | Built lazily on first use / at server start |
| A bcrypt hash in `.env` was mangled because Compose expands `$` | Compose smoke test | Single-quote the hash; documented |
| CI referenced `setup-uv@v10`, a tag that doesn't exist | First CI run | Pinned `v10.2.0` |
| CI and deploy workflows would have cancelled each other (same concurrency group) | Agent self-review before merge | Group name includes the workflow |
| Smoke tests could trip the app's own login rate limiter | Agent self-review | Smoke test accepts 401 or 429 |
| **The AWS trust policy used the wrong OIDC subject.** This repo sends GitHub's newer immutable form (`repo:owner@id/repo@id:…`), not `repo:owner/repo:…` | The first deploy failed. After two blind fixes, a temporary step printed the token's non-secret claims and made the mismatch obvious | Trust policy corrected; the claims step stays in the workflow for future debugging |
| An SSM command comment over AWS's 100-character limit; then SSM running the remote script with `dash`, which rejected `set -o pipefail` | The next two deploy attempts | One-line fixes (PRs #3 and #4), each verified by the following deploy |
| **The agent worked from the Module 3 lesson page, not the graded homework**, which was a different exercise (Kubernetes with `kind`) | Noticed late, when checking what to submit | The work became this final project; the graded homework was skipped. Lesson: read the grading page first. |
| The agent told the developer a pasted token wouldn't be echoed in the terminal; it was | The developer | Corrected immediately. Lesson: don't assert tool behaviour you haven't checked. |

The pattern: the agent's code was usually right first time in the parts that
tests covered, and wrong at the edges tests didn't reach, like cloud identity,
a vendor's shell and string limits, and which page the course grades. Those
were caught by running the real thing early and adding diagnostics instead of
guessing a second time.

## Guardrails on the agent itself

- **Least-privilege identities.** The agent runs as the server's IAM role,
  which can't read or change IAM. GitHub deploys use short-lived OIDC
  credentials that can only send SSM commands to the one instance. The
  GitHub token was fine-grained and scoped up one permission at a time
  (pull requests, then actions) as each need came up.
- **Secrets never pass through the agent.** The login password is typed into
  a no-echo prompt (`deploy/set-password.sh`), and only the bcrypt hash is
  stored. A `PreToolUse` hook blocks the agent from writing `.env` or database
  files.
- **Claude Code's own safety checks.** Auto mode refused to let the agent
  merge to `main`, and refused to create an autonomous agent spawner until
  the developer explicitly approved it (in Homework 4).
- **Documented boundaries.** [`permissions.md`](./permissions.md) lists what
  each agent capability can and can't do.

## What we'd do differently

- Read the graded homework page first, before the lesson.
- Add frontend tests from the first UI step, not after.
- Add the "print the OIDC claims" step from the start: identity mismatches
  are cheap to diagnose with evidence and slow to guess.
