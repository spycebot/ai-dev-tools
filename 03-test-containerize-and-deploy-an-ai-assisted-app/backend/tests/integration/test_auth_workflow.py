"""Authentication against the real stack: Postgres schema (via Alembic) +
SqlAlchemyCardStore + the FastAPI app, not the in-memory/SQLite stand-ins.

Auth *logic* (rate limiting, forged cookies, etc.) is already covered
exhaustively in `tests/test_auth.py` against both stores — that behaviour is
store-independent by construction. What's worth proving here is narrower:
that the real Postgres-backed app gates correctly end-to-end, and that a
session survives the backend reconnecting to the database (e.g. a
process restart against the same RDS instance).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.sqlalchemy_store import SqlAlchemyCardStore
from app.db import make_session_factory
from tests.conftest import TEST_AUTH_CONFIG, TEST_PASSWORD

pytestmark = pytest.mark.integration


def test_cards_are_gated_until_login(migrated_engine):
    store = SqlAlchemyCardStore(make_session_factory(migrated_engine))
    client = TestClient(create_app(store, auth_config=TEST_AUTH_CONFIG))

    assert client.get("/api/cards").status_code == 401

    login = client.post("/api/login", json={"password": TEST_PASSWORD})
    assert login.status_code == 200
    assert client.get("/api/cards").status_code == 200


def test_session_survives_a_fresh_connection_to_the_same_database(migrated_engine):
    """Log in against one app instance, then hit a *second* instance backed
    by a fresh session factory on the same database/engine — standing in for
    a backend restart that reconnects to the same RDS instance. The signed
    session cookie doesn't depend on any server-side state, so it should
    still authenticate.
    """
    store_a = SqlAlchemyCardStore(make_session_factory(migrated_engine))
    client = TestClient(create_app(store_a, auth_config=TEST_AUTH_CONFIG))
    client.post("/api/login", json={"password": TEST_PASSWORD})
    session_cookie = client.cookies["cc_session"]

    store_b = SqlAlchemyCardStore(make_session_factory(migrated_engine))
    fresh_app_client = TestClient(create_app(store_b, auth_config=TEST_AUTH_CONFIG))
    fresh_app_client.cookies.set("cc_session", session_cookie)

    assert fresh_app_client.get("/api/session").json() == {"authenticated": True}
    assert fresh_app_client.get("/api/cards").status_code == 200


def test_logout_then_relogin_round_trip(pg_client: TestClient):
    assert pg_client.get("/api/cards").status_code == 200

    pg_client.post("/api/logout")
    assert pg_client.get("/api/cards").status_code == 401

    pg_client.post("/api/login", json={"password": TEST_PASSWORD})
    assert pg_client.get("/api/cards").status_code == 200
