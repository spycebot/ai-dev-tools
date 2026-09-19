"""End-to-end card workflows against the real stack (Postgres schema via
Alembic, SqlAlchemyCardStore, the FastAPI app) — a frontend-shaped sequence
of API calls (create → edit → move/reorder → delete), plus proof that data
outlives the process, the way it must in production.

Per-field CRUD edge cases (validation, 404s, etc.) are already covered by
`tests/test_cards.py` against both stores; that's store-independent and not
worth re-testing here. This file is about the pieces that only show up with
a *real*, separately-provisioned database: migrated schema, reconnection,
and the full column/position bookkeeping across a realistic session.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import make_session_factory
from app.main import create_app
from app.sqlalchemy_store import SqlAlchemyCardStore
from tests.conftest import TEST_AUTH_CONFIG, TEST_PASSWORD

pytestmark = pytest.mark.integration


def _client_on(engine) -> TestClient:
    store = SqlAlchemyCardStore(make_session_factory(engine))
    client = TestClient(create_app(store, auth_config=TEST_AUTH_CONFIG))
    response = client.post("/api/login", json={"password": TEST_PASSWORD})
    assert response.status_code == 200, response.text
    return client


def test_create_edit_move_delete_round_trip(pg_client: TestClient):
    created = pg_client.post(
        "/api/cards",
        json={"title": "Write the deployment doc", "priority": "high"},
    )
    assert created.status_code == 201
    card = created.json()
    assert card["column"] == "todo"
    assert card["position"] == 0

    edited = pg_client.patch(
        f"/api/cards/{card['id']}",
        json={"description": "Covers ECS, RDS, and the CI/CD pipeline."},
    )
    assert edited.status_code == 200
    assert edited.json()["description"] == "Covers ECS, RDS, and the CI/CD pipeline."

    moved = pg_client.post(
        f"/api/cards/{card['id']}/move",
        json={"column": "in_progress", "position": 0},
    )
    assert moved.status_code == 200
    [moved_card] = moved.json()
    assert moved_card["column"] == "in_progress"

    deleted = pg_client.delete(f"/api/cards/{card['id']}")
    assert deleted.status_code == 204
    assert pg_client.get(f"/api/cards/{card['id']}").status_code == 404


def test_reordering_within_a_column_updates_positions(pg_client: TestClient):
    ids = []
    for title in ["a", "b", "c"]:
        response = pg_client.post("/api/cards", json={"title": title})
        ids.append(response.json()["id"])

    # Move the last card to the front of the same column.
    result = pg_client.post(
        f"/api/cards/{ids[2]}/move", json={"column": "todo", "position": 0}
    )
    assert result.status_code == 200

    todo_order = [c["id"] for c in pg_client.get("/api/cards").json() if c["column"] == "todo"]
    assert todo_order == [ids[2], ids[0], ids[1]]


def test_data_survives_a_fresh_connection_to_the_same_database(migrated_engine):
    """Standing in for a real deploy: create data through one connection,
    then read it back through a brand-new engine/session pair on the same
    database — the way a redeployed ECS task reconnects to the same RDS
    instance rather than keeping any in-process state.
    """
    first = _client_on(migrated_engine)
    created = first.post("/api/cards", json={"title": "Provision RDS"}).json()

    second = _client_on(migrated_engine)
    cards = second.get("/api/cards").json()

    assert [c["id"] for c in cards] == [created["id"]]
    assert cards[0]["title"] == "Provision RDS"
