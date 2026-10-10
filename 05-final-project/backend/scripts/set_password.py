#!/usr/bin/env python3
"""Generate (or rotate) the Card Catalog owner password.

There's one account and one shared password — no database, no email, no
self-service reset. This script is how you set or change it: run it, paste
the printed lines into `backend/.env`, and restart the backend. It never
touches the running server or the database.

    uv run python scripts/set_password.py
"""

from __future__ import annotations

import getpass
import secrets

import bcrypt


def main() -> None:
    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords didn't match — nothing generated.")
    if len(password) < 8:
        raise SystemExit("Use at least 8 characters.")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )

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
