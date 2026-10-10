# Agent Extension Pack — requirement map

Module 5 deliverable for the Card Catalog app (this directory,
`05-final-project/`). Module source:
[`05-agent-capabilities`](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/tree/main/05-agent-capabilities).

| Requirement | Satisfied by |
|---|---|
| 1 project instructions file | [`AGENTS.md`](../AGENTS.md) ("Agent Capabilities Quick Reference" section) + [`CLAUDE.md`](../CLAUDE.md) (`@AGENTS.md` import, Claude-Code-specific) |
| 1 reusable workflow/skill/command | [`.claude/skills/debug-ci-failure/SKILL.md`](../.claude/skills/debug-ci-failure/SKILL.md) |
| 1 specialized subagent | [`.claude/agents/api-reviewer.md`](../.claude/agents/api-reviewer.md) |
| 1 MCP tool/server | [`mcp-server/`](../mcp-server/) (`run_backend_tests`, `check_api_contract`, `run_frontend_lint`), registered via [`.mcp.json`](../.mcp.json) |
| 1 hook or guardrail | [`.claude/hooks/block-secrets-write.py`](../.claude/hooks/block-secrets-write.py), wired in [`.claude/settings.json`](../.claude/settings.json) |
| 1 plugin/extension package OR custom agent | [`plugins/ai-devtools-agent-pack/`](../plugins/ai-devtools-agent-pack/) — generalized, installable packaging of the skill + subagent + hook |
| 1 permission/security note | [`permissions.md`](./permissions.md) |

## Where each piece lives

Claude Code (and most agent tools) discover `AGENTS.md`/`CLAUDE.md`,
`.claude/skills/`, `.claude/agents/`, `.claude/settings.json`, and `.mcp.json`
relative to the directory an agent is working in, so the live config sits
at the top of this project. The MCP server's source (`mcp-server/`) and the
generalized, installable copy of the skill, subagent and hook
(`plugins/ai-devtools-agent-pack/`) sit next to it.

These pieces were first built in a separate `04-agent-capabilities/` folder
for Module 5, then moved here with the app for the final project.

## Demo

See [`agent-demo.md`](./agent-demo.md) for the walkthrough of the module's six-step demo
script against this pack.

## Relationship to Module 4

This pack's MCP server and subagent are deliberately dev-tooling-scoped
(read-only / test-only, see [`permissions.md`](./permissions.md)) rather than
production-responder-scoped. Module 4's incident responder is a separate,
far more restricted capability set and should not reuse this pack's
components as-is.
