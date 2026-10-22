"""The write-path smoke test deploy.sh runs on staging (scripts/smoke_write.py).

Runs it against the real app through TestClient, and checks it catches the
2026-10-22 game-day regression and still cleans up after itself.
"""

import pytest
from fastapi.testclient import TestClient

from app import board
from app.main import create_app
from scripts.smoke_write import SmokeFailure, run
from tests.conftest import TEST_AUTH_CONFIG


def _request(store):
    client = TestClient(create_app(store, auth_config=TEST_AUTH_CONFIG), raise_server_exceptions=False)
    # Sign the session the way smoke_write.main() does in the container.
    client.cookies.set("cc_session", TEST_AUTH_CONFIG.make_session_token())

    def request(method, path, body):
        response = client.request(method, path, json=body)
        try:
            return response.status_code, response.json()
        except ValueError:
            return response.status_code, response.text

    return request


def test_passes_and_leaves_the_board_as_it_was(store):
    before = [c.id for c in store.list_cards()]
    assert run(_request(store)) == [
        "create card",
        "move to the end of done",
        "move to the end of in_progress",
        "delete card",
    ]
    assert [c.id for c in store.list_cards()] == before


def test_catches_the_game_day_regression_and_still_deletes_the_card(store, monkeypatch):
    def broken_plan_move(cards, card_id, column, position):
        destination = [c for c in board.column_sorted(cards, column) if c.id != card_id]
        destination[position]  # df9cbe0: no clamp, IndexError past the end
        raise AssertionError("unreachable")

    monkeypatch.setattr(board, "plan_move", broken_plan_move)
    with pytest.raises(SmokeFailure, match="move to the end of done: HTTP 500"):
        run(_request(store))
    assert store.list_cards() == []


def test_fails_without_a_valid_session(store):
    client = TestClient(create_app(store, auth_config=TEST_AUTH_CONFIG))

    def request(method, path, body):
        response = client.request(method, path, json=body)
        return response.status_code, response.json()

    with pytest.raises(SmokeFailure, match="create card: HTTP 401"):
        run(request)
