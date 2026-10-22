"""Write-path smoke test: create a card, move it, delete it.

`deploy.sh` runs this inside the new **staging** container after the HTTP
smoke test, because that one only proves the app is up, not that people can
use it: on 2026-10-22 a build that failed every move to the end of a column
passed it (docs/operations-and-security-report.md, audit F18).

    python -m scripts.smoke_write          # in the container, from /app

It signs its own session with the container's AUTH_SECRET_KEY, exactly as a
login would, so no password is needed and the session token never leaves
this process. It talks to the app on 127.0.0.1:8000, creates one card titled
"smoke test", moves it to the end of two columns, and always deletes it
again. Exits non-zero, with the failing step, on any unexpected response.
Never run it against production: it writes to the board.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable

from app.auth import COOKIE_NAME, default_auth_config

# (method, path, JSON body or None) -> (status code, decoded JSON or None)
Request = Callable[[str, str, dict | None], tuple[int, object]]

PAST_THE_END = 10_000  # the regression case: a position beyond the last card
TITLE = "smoke test (deploy.sh; deleted automatically)"


class SmokeFailure(Exception):
    pass


def _expect(step: str, status: int, wanted: int, body: object) -> None:
    if status != wanted:
        raise SmokeFailure(f"{step}: HTTP {status}, expected {wanted}: {body}")


def _check_last(step: str, board: object, card_id: str, column: str) -> None:
    in_column = sorted(
        (c for c in board if c["column"] == column), key=lambda c: c["position"]
    )
    if not in_column or in_column[-1]["id"] != card_id:
        raise SmokeFailure(f"{step}: card is not last in {column}")


def run(request: Request) -> list[str]:
    """Run the checks; return what passed, or raise SmokeFailure."""
    passed = []
    status, card = request("POST", "/api/cards", {"title": TITLE})
    _expect("create card", status, 201, card)
    card_id = card["id"]
    try:
        passed.append("create card")
        for column in ("done", "in_progress"):
            step = f"move to the end of {column}"
            status, board = request(
                "POST",
                f"/api/cards/{card_id}/move",
                {"column": column, "position": PAST_THE_END},
            )
            _expect(step, status, 200, board)
            _check_last(step, board, card_id, column)
            passed.append(step)
    finally:
        status, body = request("DELETE", f"/api/cards/{card_id}", None)
        _expect("delete card", status, 204, body)
    passed.append("delete card")
    return passed


def http_request(base: str, token: str) -> Request:
    def request(method: str, path: str, body: dict | None) -> tuple[int, object]:
        req = urllib.request.Request(
            base + path,
            method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Cookie": f"{COOKIE_NAME}={token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status, raw = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
        try:
            return status, json.loads(raw) if raw else None
        except ValueError:  # e.g. a plain-text 500
            return status, raw.decode(errors="replace")[:200]

    return request


def main() -> int:
    token = default_auth_config().make_session_token()
    try:
        for step in run(http_request("http://127.0.0.1:8000", token)):
            print(f"ok  {step}")
    except SmokeFailure as exc:
        print(f"SMOKE FAIL: {exc}", file=sys.stderr)
        return 1
    print("write smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
