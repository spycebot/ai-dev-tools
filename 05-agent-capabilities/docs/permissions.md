# Permissions and security boundaries

What each piece of the Agent Extension Pack can and can't do, and why.

## `api-reviewer` subagent

`tools: Read, Grep, Glob, Bash` — no `Edit`, `Write`, or `MultiEdit`. It runs
in its own isolated context (a Claude Code subagent), so even if its
instructions were somehow hijacked by something it read, it has no tool
available that modifies a file. Its `Bash` access is used only to run the
existing read-only test command (`uv run pytest tests/test_openapi.py -q`);
it is not sandboxed away from running other commands, so this is a
convention enforced by its system prompt, not a hard boundary — see "What
this pack does not provide" below.

## `card-catalog-ops` MCP server

Exposes exactly three tools, all of which only *run the project's existing
test/lint commands* as a subprocess (`subprocess.run`, not `shell=True`, no
string-interpolated input):

| Tool | Can do | Cannot do |
|---|---|---|
| `run_backend_tests` | Run `uv run pytest` with a fixed marker argument | Accept arbitrary pytest args, touch the database directly |
| `check_api_contract` | Run one named test file | — |
| `run_frontend_lint` | Run `npm run lint` | — |

None of the three tools read `backend/.env`, connect to a production
database, accept a free-form shell string, or write any file. An agent
wired only to this MCP server — even a fully compromised or badly-prompted
one — cannot exfiltrate the password hash/secret key or mutate data through
it; the worst it can do is run the test suite repeatedly.

## `block-secrets-write` hook (`PreToolUse`, `Write|Edit|MultiEdit`)

A deterministic, code-level backstop — not a suggestion to a model. It
inspects the `file_path` of every `Write`/`Edit`/`MultiEdit` call before it
executes and denies (exit code 2) any write to `backend/.env` or
`backend/card_catalog.db` (project-specific version) / any `.env*` or
`*.db`/`*.sqlite*` file (plugin/generalized version). This is enforced by
Claude Code itself outside the model's control — a model "deciding" to write
there anyway still gets blocked.

## `debug-ci-failure` skill

Read-only by nature: it's a checklist of commands to run and files to grep,
invoked in the main session's own context with whatever permissions that
session already has. It adds no new capability or boundary by itself — it's
listed here for completeness, matching the deliverable's requirement list.

## What this pack does not provide

- **No sandboxing of the subagent's `Bash` tool.** Claude Code subagents
  share the host session's permission settings unless a project further
  restricts `Bash` in `.claude/settings.json` (e.g. an explicit allowlist of
  commands). This pack relies on the subagent's system prompt restricting
  itself to read-only checks, not on an enforced denylist — a gap worth
  closing before using this pattern for anything higher-stakes than a
  homework project.
- **No network egress control.** Nothing here restricts what URLs an agent
  can reach; that would need to be a sandbox or proxy policy outside
  Claude Code's own config.
- **No production credentials anywhere in this pack.** There's nothing to
  leak because nothing here is ever configured with a real `DATABASE_URL`,
  AWS credentials, or deploy access — by design, not by accident. If this
  app is later deployed (Module 3/4 work), any agent tooling given real
  production access needs its own, separate, much narrower review before
  that happens — this pack's scope stops at "can tell you if the tests
  pass," matching Module 5's dev-tooling remit rather than Module 4's
  production-responder remit.
