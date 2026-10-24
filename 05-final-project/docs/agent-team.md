# The agent team

Card Catalog is built and run by one human owner and four AI agents. Each
member has a clear job, and work passes between them only through files,
issues, pull requests and alerts, never through shared memory. This page
names every member, says what each one may touch, and shows how work moves
between them. How the team came about, and where it went wrong, is in
[`ai-workflow.md`](./ai-workflow.md). The permission details are in
[`permissions.md`](./permissions.md).

## Members

| Member | What it is | Main job | Can change code? | Can change production? |
|---|---|---|---|---|
| **Owner** | The developer (`spycebot`) | Decides what to build, reviews, merges, approves production | Yes | Yes: approves every production deploy and every prod rollback |
| **Builder** | Claude Code (main session), driven by [`AGENTS.md`](../AGENTS.md) | Turns an issue into a tested pull request | Yes, on a branch | No: can't merge to `main`, and holds no AWS or deploy credentials |
| **API reviewer** | Claude Code subagent, [`.claude/agents/api-reviewer.md`](../.claude/agents/api-reviewer.md) | Reviews API changes for contract drift, auth gaps and portability | No (no Edit or Write tools) | No |
| **Ops tools** | MCP server `card-catalog-ops`, [`mcp-server/`](../mcp-server/) | Runs the tests, the API contract check and lint for any agent | No | No |
| **Incident responder** | Headless `claude -p` inside [`incident-response/`](../incident-response/) | Investigates an alert and proposes a fix | No (Read, Grep, Glob only) | Only through the policy: rolls back staging on its own; prod only after the owner runs `approve.sh` |

Two automated gates sit between them, without a model: **CI**
([`ci.yml`](../../.github/workflows/ci.yml): lint, unit, integration,
container and security scans) and **CD**
([`deploy.yml`](../../.github/workflows/deploy.yml): staging, then
production after the owner's approval).

## Responsibilities, inputs and outputs

### Owner

- **Responsible for:** product scope, architecture choices, every secret,
  cloud console and IAM change, merging to `main`, approving production
  deploys and prod rollbacks, and every security disposition.
- **Input:** pull requests, incident records, audit findings.
- **Output:** issues with acceptance criteria, review decisions, merges,
  approvals.

### Builder

- **Responsible for:** implementing one issue at a time, with tests, docs and
  a pull request; watching the deploy afterwards; writing down surprises in
  the README's *Challenges & Notes*.
- **Input:** a GitHub issue, plus the standing context: `AGENTS.md`,
  [`_docs/specs.md`](../_docs/specs.md), [`openapi.yaml`](../openapi.yaml)
  and these docs.
- **Output:** a branch and a pull request whose description says
  `Closes #<issue>` and lists how each acceptance criterion was checked.
- **Limits:** never reads or writes `.env` files or the database (the
  `block-secrets-write` hook enforces the write side); never merges; asks the
  owner before outward-facing or hard-to-undo actions.

### API reviewer

- **Responsible for:** checking any diff that touches `backend/app/main.py`,
  `models.py`, `auth.py`, the stores, `board.py`, `orm.py` or `openapi.yaml`.
- **Input:** the Builder's diff, handed over by the Builder.
- **Output:** a list of findings (file:line, why, minimal fix) back to the
  Builder, or an explicit "no issues". It never edits.

### Ops tools (MCP server)

- **Responsible for:** giving any agent the same three fixed checks:
  `run_backend_tests`, `check_api_contract`, `run_frontend_lint`.
- **Input:** a tool call with a fixed argument.
- **Output:** the test or lint output. It accepts no free-form commands,
  doesn't read `.env` and writes nothing.

### Incident responder

- **Responsible for:** working out what broke when the 5xx alert fires, and
  proposing an action (`none`, `rollback` or `escalate`).
- **Input:** an evidence packet collected by fixed scripts before the model
  runs, with public IP addresses redacted: deploy state, the diff, metrics,
  logs, traces and a smoke test.
- **Output:** a JSON proposal that must match
  [`response.schema.json`](../incident-response/response.schema.json).
  [`policy.py`](../incident-response/policy.py), not the model, decides
  whether it runs. Every incident is recorded under
  [`incidents/`](../incident-response/incidents/).

## How work moves through the team

```text
 Owner ── issue with acceptance criteria ──► Builder
                                              │ branch, code + tests
                                              │ API change? ──► API reviewer ──► findings ──┐
                                              │ checks ──► Ops tools (MCP) ──► results ─────┤
                                              ▼                                             │
                                        pull request "Closes #n" ◄──────────────────────────┘
                                              │
                                     CI (required checks)
                                              │
 Owner ◄──────────── review ─────────────────┘
   │ merge to main
   ▼
 CD: build ──► staging (automatic, smoke tests, auto-rollback)
   │
 Owner approves ──► production (smoke tests, auto-rollback)
   │
   ▼
 5xx alert ──► Incident responder ──► proposal ──► policy.py
                                                    ├─ staging: rollback + verify, recorded
                                                    └─ prod: recorded, Owner runs approve.sh
 Incident record ──► Owner ──► new issue (the lasting fix) ──► Builder …
```

The hand-offs, in words:

1. **Owner → Builder:** a GitHub issue. The Builder doesn't start work
   without one (see `AGENTS.md`).
2. **Builder → API reviewer → Builder:** the diff goes out, findings come
   back. The Builder fixes them or explains in the PR why not.
3. **Builder → Owner:** a pull request with `Closes #n`. The Owner reviews
   and merges; merging closes the issue.
4. **Owner → production:** the Owner approves the waiting `production`
   job after checking staging ([`release-process.md`](./release-process.md#manual-approval-for-production)).
5. **Alert → Incident responder → Owner:** the incident record. On staging
   the responder may already have rolled back; on prod it waits for
   `approve.sh`. Either way the lasting fix becomes a new issue, as with
   the 2026-10-22 game day, which became audit finding F18 (#45).

## Example: F18, end to end

1. The staging game day: the responder saw 5xx on moves, proposed a
   rollback, and the policy ran it in 69 seconds
   ([incident record](../incident-response/incidents/INC-20261022-175440-staging/)).
2. The Owner read the record and asked for a lasting fix: deploy only images
   CI built, and run a write smoke test on staging.
3. The Builder implemented it on `f18-deploy-gate`, with tests, and opened
   PR #26.
4. CI passed, the Owner merged, and CD deployed it. The Builder watched the
   deploy and confirmed the new checks ran.
