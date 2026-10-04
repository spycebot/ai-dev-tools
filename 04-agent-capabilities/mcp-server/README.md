# card-catalog-ops MCP server

A minimal [MCP](https://modelcontextprotocol.io) server, built with the
official Python SDK's `FastMCP`, exposing three tools scoped to the Card
Catalog app's existing test commands:

| Tool | What it runs |
|---|---|
| `run_backend_tests(scope)` | `uv run pytest` in `backend/`, scoped to `unit` (default), `integration`, or `all` |
| `check_api_contract()` | `uv run pytest tests/test_openapi.py -q` in `backend/` |
| `run_frontend_lint()` | `npm run lint` (oxlint) in `frontend/` |

## Why these three and nothing else

The point of handing an agent an MCP server instead of raw `Bash` access is
the same point as handing a person a scoped API key instead of root: the
agent gets exactly the capability it needs for the stated job — "can I tell
if this change broke anything" — and nothing else. See
[`../docs/permissions.md`](../docs/permissions.md) for the full boundary and
what was deliberately left out (no DB write tool, no deploy tool, no
arbitrary-command tool, no `.env` read tool).

## Running it standalone

```bash
cd 04-agent-capabilities/mcp-server
uv run python server.py
```

It's registered for Claude Code via
[`../../03-test-containerize-and-deploy-an-ai-assisted-app/.mcp.json`](../../03-test-containerize-and-deploy-an-ai-assisted-app/.mcp.json),
so it starts automatically when Claude Code is working in that app directory.
