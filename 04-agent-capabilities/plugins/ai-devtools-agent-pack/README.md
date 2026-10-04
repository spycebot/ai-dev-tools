# ai-devtools-agent-pack (plugin)

A portable, installable package of the three "live" components from this
module's Agent Extension Pack:

- `skills/debug-ci-failure/` — a reusable CI-failure-triage workflow
- `agents/api-reviewer.md` — a specialized, review-only subagent
- `hooks/` — a `PreToolUse` guardrail blocking writes to secrets/database files

The project-specific originals (hardcoded to the Card Catalog app) live in
`03-test-containerize-and-deploy-an-ai-assisted-app/.claude/`. This plugin
generalizes them — placeholder commands/paths instead of this one repo's
specifics — so they can be installed in a different project instead of
copy-pasted and hand-edited.

## What's deliberately not generalized

The MCP server (`../../mcp-server/`) is not packaged into this plugin: its
three tools (`run_backend_tests`, `check_api_contract`, `run_frontend_lint`)
are wired to this specific app's test commands and directory layout. A
real generalization would need a config file mapping "unit test command" /
"lint command" per project; out of scope for this homework pass — noted
here rather than silently skipped.
