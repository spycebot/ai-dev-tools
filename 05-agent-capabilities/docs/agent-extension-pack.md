# Agent Extension Pack — requirement map

Module 5 deliverable for the Card Catalog app (built in Modules 2–3,
`../03-test-containerize-and-deploy-an-ai-assisted-app/`). Module source:
[`05-agent-capabilities`](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/tree/main/05-agent-capabilities).

| Requirement | Satisfied by |
|---|---|
| 1 project instructions file | [`../03-test-containerize-and-deploy-an-ai-assisted-app/AGENTS.md`](../03-test-containerize-and-deploy-an-ai-assisted-app/AGENTS.md) ("Agent Capabilities Quick Reference" section) + [`CLAUDE.md`](../03-test-containerize-and-deploy-an-ai-assisted-app/CLAUDE.md) (`@AGENTS.md` import, Claude-Code-specific) |
| 1 reusable workflow/skill/command | [`.claude/skills/debug-ci-failure/SKILL.md`](../03-test-containerize-and-deploy-an-ai-assisted-app/.claude/skills/debug-ci-failure/SKILL.md) |
| 1 specialized subagent | [`.claude/agents/api-reviewer.md`](../03-test-containerize-and-deploy-an-ai-assisted-app/.claude/agents/api-reviewer.md) |
| 1 MCP tool/server | [`mcp-server/`](../mcp-server/) (`run_backend_tests`, `check_api_contract`, `run_frontend_lint`), registered via [`.mcp.json`](../03-test-containerize-and-deploy-an-ai-assisted-app/.mcp.json) |
| 1 hook or guardrail | [`.claude/hooks/block-secrets-write.py`](../03-test-containerize-and-deploy-an-ai-assisted-app/.claude/hooks/block-secrets-write.py), wired in [`.claude/settings.json`](../03-test-containerize-and-deploy-an-ai-assisted-app/.claude/settings.json) |
| 1 plugin/extension package OR custom agent | [`plugins/ai-devtools-agent-pack/`](../plugins/ai-devtools-agent-pack/) — generalized, installable packaging of the skill + subagent + hook |
| 1 permission/security note | [`permissions.md`](./permissions.md) |

## Why the live config lives in the app directory, not here

Claude Code (and most agent tools) discover `AGENTS.md`/`CLAUDE.md`,
`.claude/skills/`, `.claude/agents/`, `.claude/settings.json`, and `.mcp.json`
relative to the directory an agent is actually working in. For the demo
script below to work as written — "the agent reads the project
instructions," "a hook prevents/checks an action" — those files have to live
in `03-test-containerize-and-deploy-an-ai-assisted-app/`, the app being
extended, not in this module folder. This folder (`05-agent-capabilities/`)
holds the reusable/portable artifacts (the MCP server's source, the
generalized plugin package) and the documentation tying it all together.

## Demo

See [`demo.md`](./demo.md) for the walkthrough of the module's six-step demo
script against this pack.

## Relationship to Module 4

The devops/observability module
([`../04-devops-and-ovservability/`](../04-devops-and-ovservability/)) is
being built separately, on the AWS ECS host (Docker-dependent — the
observability stack's `compose.yaml` needs a container runtime this app's
own README already ruled out installing on the shared OVH box, for the same
reason: see that README's "Challenges & Notes" on Docker). This pack's
MCP server and subagent are deliberately dev-tooling-scoped (read-only /
test-only, see [`permissions.md`](./permissions.md)) rather than
production-responder-scoped — Module 4's responder, when built, is a
separate, far more restricted capability set and should not reuse this
pack's components as-is.
