# Demo script

Module 5's suggested demo, run against this pack. All commands assume
`cd 03-test-containerize-and-deploy-an-ai-assisted-app` first (the directory
Claude Code needs to be working in for the project-level config to load).

## 1. The agent reads the project instructions

Start a Claude Code session in the app directory and ask something that
requires the architecture summary, e.g. "what store does the backend use by
default, and where do column/position rules live?" The answer should come
from `AGENTS.md`'s "Agent Capabilities Quick Reference" section
(`SqlAlchemyCardStore`, `app/board.py`) without needing to grep the code.

## 2. A reusable workflow is invoked

Break a test on purpose (e.g. temporarily rename `board_column` back to
`column` in `app/orm.py`) and ask Claude Code to use the `debug-ci-failure`
skill. It should run the unit suite first, hit the reserved-word failure,
and — per the skill's step 2 — recognize it as the documented "reserved SQL
words" gotcha rather than re-deriving the cause from scratch.

## 3. A specialized subagent reviews an API change

Make a small API change (e.g. add a field to `CardUpdate` without updating
`openapi.yaml`) and ask Claude Code to have the `api-reviewer` subagent
review it. Expect it to flag the contract drift (check #1 in its
instructions) and, if the change also skipped `Depends(require_auth)`,
flag the auth gap (check #2) — it should not propose an edit itself, only
report findings.

## 4. The agent calls an MCP tool

Ask "do the backend tests currently pass?" — Claude Code should call the
`card-catalog-ops` MCP server's `run_backend_tests` tool rather than running
`uv run pytest` directly via `Bash`, since the tool is registered and scoped
for exactly this question.

## 5. A hook or guardrail prevents, formats, checks, or logs an action

Ask Claude Code to "write a test value directly into backend/.env" — the
`PreToolUse` hook should deny the `Write`/`Edit` call (exit 2) with the
message from `block-secrets-write.py`, before any file is touched.

## 6. The student reviews the final diff

`git status` / `git diff` from the repo root
(`/var/www/terzotech.net/ai-dev-tools/`) to confirm only the intended
test-break/revert and API-change-for-demo edits exist, then discard them —
none of steps 2–5 above should be left as real changes to the app.
