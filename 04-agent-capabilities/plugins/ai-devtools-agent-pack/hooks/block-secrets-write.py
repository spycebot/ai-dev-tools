#!/usr/bin/env python3
"""PreToolUse guardrail: block agent writes to secrets files or database files.

Generalized version of the project-specific hook at
03-test-containerize-and-deploy-an-ai-assisted-app/.claude/hooks/block-secrets-write.py
(which hardcodes that project's exact paths). This one matches by pattern so
it works across projects: reads the hook payload (JSON) from stdin, and
denies the tool call (exit 2, message on stderr) if the target file is:

  - a dotenv file (`.env`, `.env.local`, `.env.production`, ...) but not an
    example/template (`.env.example`, `.env.sample`, `.env.template`)
  - a SQLite database file (`*.db`, `*.sqlite`, `*.sqlite3`)

Adjust `_is_blocked` if a project needs different boundaries (e.g. also
blocking `*.pem`/`*.key`, or allowlisting a specific `.env.test`).
"""

from __future__ import annotations

import json
import re
import sys

_ENV_EXAMPLE_RE = re.compile(r"\.env\.(example|sample|template)$")
_ENV_RE = re.compile(r"(^|/)\.env(\.\w+)?$")
_DB_SUFFIXES = (".db", ".sqlite", ".sqlite3")


def _is_blocked(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if _ENV_EXAMPLE_RE.search(normalized):
        return False
    if _ENV_RE.search(normalized):
        return True
    return normalized.endswith(_DB_SUFFIXES)


def _paths_from(tool_input: dict) -> list[str]:
    if "file_path" in tool_input:
        return [tool_input["file_path"]]
    return []


def main() -> int:
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input", {})
    for path in _paths_from(tool_input):
        if _is_blocked(path):
            print(
                f"Blocked: {path} looks like a secrets or database file "
                "(see hooks/block-secrets-write.py). If this is a false "
                "positive, adjust _is_blocked for this project.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
