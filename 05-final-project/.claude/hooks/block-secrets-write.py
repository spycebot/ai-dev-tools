#!/usr/bin/env python3
"""PreToolUse guardrail: block agent writes to secrets or the dev database.

Registered in .claude/settings.json for Write/Edit/MultiEdit. Reads the hook
payload (JSON) from stdin, checks the target file path(s), and denies the
tool call (exit 2, message on stderr) if it touches:

  - backend/.env            (real secrets: AUTH_PASSWORD_HASH, AUTH_SECRET_KEY)
  - backend/card_catalog.db (the dev SQLite database)

`.env.example` is explicitly allowed — it holds no real values. This is a
guardrail against an agent "helpfully" writing directly to `.env` (which
belongs to a human running scripts/set_password.py) or silently hand-editing
the dev database file instead of going through the API/store.
"""

from __future__ import annotations

import json
import sys

_BLOCKED_SUFFIXES = ("backend/.env", "backend/card_catalog.db")


def _paths_from(tool_input: dict) -> list[str]:
    if "file_path" in tool_input:
        return [tool_input["file_path"]]
    if "edits" in tool_input:  # MultiEdit-style payloads, defensively handled
        return [tool_input.get("file_path", "")]
    return []


def main() -> int:
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input", {})
    for path in _paths_from(tool_input):
        normalized = path.replace("\\", "/")
        for blocked in _BLOCKED_SUFFIXES:
            if normalized.endswith(blocked):
                print(
                    f"Blocked: {path} is a secrets/data file managed outside "
                    "the agent (see .claude/hooks/block-secrets-write.py). "
                    "Edit backend/.env.example instead, or ask the user to "
                    "run scripts/set_password.py for real credentials.",
                    file=sys.stderr,
                )
                return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
