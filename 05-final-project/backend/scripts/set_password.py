#!/usr/bin/env python3
"""Generate (or rotate) the Card Catalog owner password.

There's one account and one shared password — no database, no email, no
self-service reset. This script is how you set or change it: run it, paste
the printed lines into `backend/.env`, and restart the backend. It never
touches the running server or the database.

    uv run python scripts/set_password.py
    uv run python scripts/set_password.py --env-file ../.env   # write it instead

With `--env-file`, both values are written into that file (an existing
AUTH_PASSWORD_HASH / AUTH_SECRET_KEY line is replaced, the rest is kept)
and nothing secret is printed. The hash is single-quoted so Docker Compose
doesn't expand its `$`s. `make up` uses this on first run.
"""

from __future__ import annotations

import argparse
import getpass
import re
import secrets
from pathlib import Path

import bcrypt


def write_env_file(path: Path, password_hash: str, secret_key: str) -> None:
    """Set both AUTH_* lines in an env file, keeping every other line."""
    values = {
        "AUTH_PASSWORD_HASH": f"'{password_hash}'",  # quoted: Compose expands $
        "AUTH_SECRET_KEY": secret_key,
    }
    lines = path.read_text().splitlines() if path.exists() else []
    for name, value in values.items():
        pattern = re.compile(rf"^\s*{name}\s*=")
        matches = [i for i, line in enumerate(lines) if pattern.match(line)]
        if matches:
            lines[matches[0]] = f"{name}={value}"
            lines = [line for i, line in enumerate(lines) if i not in matches[1:]]
        else:
            lines.append(f"{name}={value}")
    # Rewrite in place rather than rename: the file may be a bind mount.
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env-file", type=Path, help="write both values into this file")
    args = parser.parse_args()

    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords didn't match — nothing generated.")
    if len(password) < 8:
        raise SystemExit("Use at least 8 characters.")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )

    if args.env_file:
        write_env_file(args.env_file, password_hash, secrets.token_urlsafe(32))
        print(f"Wrote AUTH_PASSWORD_HASH and AUTH_SECRET_KEY to {args.env_file}.")
        return

    print("\nAdd this to backend/.env, replacing any existing AUTH_PASSWORD_HASH line:\n")
    print(f"AUTH_PASSWORD_HASH={password_hash}")
    print(
        "\nIf backend/.env doesn't already have an AUTH_SECRET_KEY, also add "
        "this (generate it once and keep it stable — changing it logs "
        "everyone out, but that's harmless):\n"
    )
    print(f"AUTH_SECRET_KEY={secrets.token_urlsafe(32)}")
    print("\nThen restart the backend for the change to take effect.")


if __name__ == "__main__":
    main()
