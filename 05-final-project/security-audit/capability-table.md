# Capability table

Every agent, agent extension and automation in this repo that can act on
the code or the servers. For each one: what it can read, what it can
change, which credentials it holds, and **what enforces that limit**. The
last column is the one that matters. A limit written in a prompt is a
request to the model; a limit enforced by code or by IAM still holds when
the model is wrong or has been manipulated.

Last reviewed: 2026-10-22 ([baseline](runs/2026-10-14-baseline/summary.md),
[operations run](runs/2026-10-22-operations/summary.md)).

## Coding agents and extensions

| Component | Reads | Changes / runs | Credentials | Network | Enforced by | Provenance |
|---|---|---|---|---|---|---|
| **Claude Code, main session** (developer's agent) | The repo, and anything the `ubuntu` user can read on the host | Whatever the user approves per tool call, in Claude Code's permission mode | The user's GitHub CLI token (fine-grained PAT, limited to the repos and permissions the owner granted); no AWS access keys are configured for the agent, but the host has the EC2 instance role the SSM agent uses (not reviewed in this run) | Open | Claude Code permission prompts; the hook below; the PAT's scope; branch protection (only the owner merges to `main`) | Anthropic; the version installed by the user |
| **`api-reviewer` subagent** (`.claude/agents/`) | Repo files (Read, Grep, Glob) | `Bash`: by its prompt, only `pytest tests/test_openapi.py` | Inherits the session's | Inherits | No Edit/Write tools (**code**); Bash use limited by **prompt only** | This repo; reviewed in PR |
| **`card-catalog-ops` MCP server** (`mcp-server/`) | Test output | Three fixed commands: backend pytest (fixed markers), the API contract test, frontend lint. No free-form input reaches a shell | None | None of its own; tests run locally | **Code**: fixed argv lists, `subprocess.run` without a shell, scope validated against a dict | This repo; deps pinned in `mcp-server/uv.lock` |
| **`debug-ci-failure` skill** (`.claude/skills/`) | Instructions only | Nothing by itself; uses the session's tools | None | n/a | n/a (adds no capability) | This repo |
| **`block-secrets-write` hook** (`.claude/hooks/`) | The target path of each Write/Edit | Denies writes to `.env`, `prod.env`, `staging.env`, `backend/card_catalog.db` | None | None | **Code**, run by Claude Code before the tool executes. Does **not** cover writes made through `Bash` | This repo; widened in audit F05 |
| **Agent pack plugin** (`plugins/ai-devtools-agent-pack/`) | Same as the three rows above, generalized | Same; its hook blocks any `.env*` except examples, and `*.db`/`*.sqlite*` | None | None | Same as above | This repo; installed only by explicit `/plugin install` |

## Automations that hold production credentials

| Component | Can do | Credentials | Enforced by | Provenance |
|---|---|---|---|---|
| **CI** (`ci.yml`) | Build and test; no deploy | `GITHUB_TOKEN`, `contents: read` | Workflow `permissions:` | Actions pinned by commit SHA (audit F01) |
| **Deploy build job** | Push images to `ghcr.io/spycebot/card-catalog` | `GITHUB_TOKEN`, `packages: write` | Job-level `permissions:`; runs only after CI passes on `main` | SHA-pinned actions |
| **Deploy staging / production / rollback** | Run `deploy/ssm-run.sh` on the one app instance via SSM | Short-lived AWS credentials via OIDC for the role `card-catalog-github-deploy` | **IAM**: the trust policy accepts only this repo's `staging`/`production` environments (immutable OIDC subject); the role can only send `AWS-RunShellScript` to instance `i-03608727285d00358` | SHA-pinned actions; `docs/deployment.md` |
| **Server scripts** (`deploy/*.sh`) | Migrate, switch images, roll back, set the password | Root on the instance (via SSM); read the env files | Code review + branch protection; fetched by exact commit SHA | This repo |

## Operations automations (only while the monitoring stack runs)

| Component | Reads | Changes / runs | Credentials | Enforced by | Provenance |
|---|---|---|---|---|---|
| **Incident responder** (`incident-response/responder.py`, a host process) | Grafana's alert webhook; Prometheus, Loki and Tempo through Grafana; `images.env`; `docker logs` of the alerting container | Writes `incidents/<id>/`. Runs exactly two commands, with fixed argv from `autonomy-policy.yaml`: `deploy.sh rollback <env>` and `verify-recovery.sh`. Staging: on its own (level 2). Prod: only after a human runs `approve.sh` (level 1). At most one automatic action per environment per hour | Grafana admin (localhost only, F16); runs as `ubuntu`, which is in the `docker` group (root-equivalent on the host). No AWS or GitHub credentials | **Code**: `policy.py` (11 tests) decides from facts the responder gathers itself, never from model text; the environment comes from an allowlist; webhook answers only private/loopback clients (F17) | This repo |
| **Responder's agent** (`claude -p`, started by the responder) | Repo files only: `Read`, `Grep`, `Glob`. Reads outside the repo are denied by headless mode, and `--disallowedTools` denies `/srv`, `~/.claude`, `~/.ssh`, `~/.aws`, `~/setup`, and every `.env` and `*.db` (F15) | Nothing. Its only output is a JSON proposal, validated against `response.schema.json` | The user's Claude Code login | **Code**: `--tools`, `--strict-mcp-config` (no MCP servers), deny rules; output is a proposal that `policy.py` may reject. Evidence is redacted of public IPs before it runs (F14) | Anthropic CLI; prompt in `responder-task.md` |
| **Monitoring stack** (`observability/`) | OTLP from prod and staging (requests, ERROR logs with stack traces, traces) | Its own volumes; Grafana sends the alert webhook | Grafana admin (F16) | Grafana published on 127.0.0.1 only; the collector is on the app's Docker network, nothing else is published | Images pinned by version tag |

## Not yet in place

- **Snyk Agent Scan.** Not run yet: it sends the MCP server's and the
  agent pack's tool descriptions to Snyk's API, which needs the owner's
  approval first (see [`ai-tool-policy.md`](ai-tool-policy.md)). The
  tables above are the manual inventory it would check.
- **The host's EC2 instance role.** The SSM agent needs it, and any process
  on the host, including a coding agent, can request its credentials from
  the instance metadata service. Its permissions should be checked in IAM
  and kept to SSM-only (`AmazonSSMManagedInstanceCore`).
- **Bash write coverage.** Neither hook sees a `Bash` command that writes
  a secrets file, so the main session's permission prompts are the only
  guard there.
