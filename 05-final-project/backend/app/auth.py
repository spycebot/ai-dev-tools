"""Password gate for the single-user Card Catalog app.

There is exactly one account (the owner) and one shared password — no user
table, no signup, no email-based "forgot password" flow. The password's
bcrypt hash lives in the `AUTH_PASSWORD_HASH` environment variable; sessions
are a signed, timed cookie (`itsdangerous`), so there's no server-side
session store to manage either. Run `scripts/set_password.py` to generate a
hash and rotate the password — see `.env.example`.

`AuthConfig` is injectable into `create_app()` (mirrors how `CardStore` is
injected) so tests can use a fixed, low-cost test password instead of
requiring real environment variables.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel

COOKIE_NAME = "cc_session"
_SESSION_PAYLOAD = "authenticated"
_COOKIE_SALT = "cc-session"


class LoginRequest(BaseModel):
    password: str


@dataclass
class AuthConfig:
    """Everything the auth layer needs to check a password and a session."""

    password_hash: str
    secret_key: str
    session_ttl_seconds: int = 60 * 60 * 24 * 30  # 30 days
    cookie_secure: bool = True
    max_attempts: int = 5
    window_seconds: int = 300

    def verify_password(self, candidate: str) -> bool:
        return bcrypt.checkpw(
            candidate.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def make_session_token(self) -> str:
        return self._serializer().dumps(_SESSION_PAYLOAD)

    def verify_session_token(self, token: str | None) -> bool:
        if not token:
            return False
        try:
            payload = self._serializer().loads(
                token, max_age=self.session_ttl_seconds
            )
        except (BadSignature, SignatureExpired):
            return False
        return payload == _SESSION_PAYLOAD

    def _serializer(self) -> URLSafeTimedSerializer:
        # Cheap to build per call; avoids storing a non-dataclass field.
        return URLSafeTimedSerializer(self.secret_key, salt=_COOKIE_SALT)


def default_auth_config() -> AuthConfig:
    """Build an `AuthConfig` from the environment. Fails loudly if unset.

    This app is password-gated by design — refusing to start without real
    credentials configured is the point, not an inconvenience. Tests inject
    their own `AuthConfig` instead of going through this function.
    """
    password_hash = os.environ.get("AUTH_PASSWORD_HASH")
    secret_key = os.environ.get("AUTH_SECRET_KEY")
    if not password_hash or not secret_key:
        raise RuntimeError(
            "AUTH_PASSWORD_HASH and AUTH_SECRET_KEY must be set before the "
            "app will start. Run `uv run python scripts/set_password.py` to "
            "generate both, then put them in backend/.env (see .env.example)."
        )
    cookie_secure = os.environ.get("AUTH_COOKIE_SECURE", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    return AuthConfig(
        password_hash=password_hash,
        secret_key=secret_key,
        cookie_secure=cookie_secure,
    )


class RateLimiter:
    """A small in-memory brute-force brake, keyed by client IP.

    Process-local: it resets on restart and isn't shared across multiple
    worker processes. That's an accepted limit for this single-instance app
    (see README) — not a substitute for a real rate-limiting layer if this
    ever needs to scale past one owner.
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        """True if `key` is still allowed to attempt a login."""
        window_start = time.monotonic() - self.window_seconds
        attempts = [t for t in self._attempts[key] if t >= window_start]
        self._attempts[key] = attempts
        return len(attempts) < self.max_attempts

    def record_failure(self, key: str) -> None:
        self._attempts[key].append(time.monotonic())

    def record_success(self, key: str) -> None:
        self._attempts.pop(key, None)
