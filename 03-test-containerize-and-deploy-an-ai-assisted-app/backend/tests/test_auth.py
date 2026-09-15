"""Auth behaviour: login/logout/session, and that cards routes are gated.

Uses the parametrized `store` fixture from conftest (memory + sqlalchemy) but
builds its own `TestClient`s rather than using the `client`/`seeded_client`
fixtures, since those start out logged in — the whole point here is to
exercise the logged-out and login/logout transitions.
"""

from fastapi.testclient import TestClient

from app.auth import AuthConfig
from app.main import create_app
from tests.conftest import TEST_AUTH_CONFIG, TEST_PASSWORD


def _client(store) -> TestClient:
    return TestClient(create_app(store, auth_config=TEST_AUTH_CONFIG))


def test_cards_routes_require_a_session(store):
    response = _client(store).get("/api/cards")
    assert response.status_code == 401


def test_health_does_not_require_a_session(store):
    response = _client(store).get("/health")
    assert response.status_code == 200


def test_wrong_password_is_rejected(store):
    client = _client(store)
    response = client.post("/api/login", json={"password": "definitely not it"})
    assert response.status_code == 401
    # No cookie set, and cards are still gated.
    assert "cc_session" not in response.cookies
    assert client.get("/api/cards").status_code == 401


def test_correct_password_logs_in_and_unlocks_cards(store):
    client = _client(store)
    response = client.post("/api/login", json={"password": TEST_PASSWORD})
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    assert client.get("/api/cards").status_code == 200


def test_session_endpoint_reflects_login_state(store):
    client = _client(store)
    assert client.get("/api/session").json() == {"authenticated": False}

    client.post("/api/login", json={"password": TEST_PASSWORD})
    assert client.get("/api/session").json() == {"authenticated": True}


def test_logout_clears_the_session(store):
    client = _client(store)
    client.post("/api/login", json={"password": TEST_PASSWORD})
    assert client.get("/api/cards").status_code == 200

    logout_response = client.post("/api/logout")
    assert logout_response.status_code == 200
    assert client.get("/api/cards").status_code == 401


def test_a_forged_cookie_is_rejected(store):
    client = _client(store)
    client.cookies.set("cc_session", "not-a-real-signed-token")
    assert client.get("/api/cards").status_code == 401


def test_a_session_signed_with_a_different_secret_is_rejected(store):
    other_config = AuthConfig(
        password_hash=TEST_AUTH_CONFIG.password_hash,
        secret_key="a-completely-different-secret",
    )
    forged_token = other_config.make_session_token()

    client = _client(store)
    client.cookies.set("cc_session", forged_token)
    assert client.get("/api/cards").status_code == 401


def test_repeated_failed_logins_are_rate_limited(store):
    client = _client(store)
    for _ in range(TEST_AUTH_CONFIG.max_attempts):
        response = client.post("/api/login", json={"password": "wrong"})
        assert response.status_code == 401

    limited = client.post("/api/login", json={"password": "wrong"})
    assert limited.status_code == 429

    # Even the correct password is refused while rate-limited.
    still_limited = client.post("/api/login", json={"password": TEST_PASSWORD})
    assert still_limited.status_code == 429


def test_a_successful_login_resets_the_rate_limit(store):
    client = _client(store)
    client.post("/api/login", json={"password": "wrong"})
    client.post("/api/login", json={"password": TEST_PASSWORD})

    # Back under the limit after a success; a few more wrong guesses don't
    # immediately trip the limiter again.
    response = client.post("/api/login", json={"password": "wrong"})
    assert response.status_code == 401
