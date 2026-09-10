import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.store import InMemoryCardStore


@pytest.fixture
def client() -> TestClient:
    """A client backed by an empty store (no seed cards)."""
    return TestClient(create_app(InMemoryCardStore(seed=False)))


@pytest.fixture
def seeded_client() -> TestClient:
    """A client backed by a store carrying the four seed cards."""
    return TestClient(create_app(InMemoryCardStore(seed=True)))


def make_card(client: TestClient, **overrides) -> dict:
    """Create a card through the API and return its JSON body."""
    body = {"title": "Task", **overrides}
    response = client.post("/api/cards", json=body)
    assert response.status_code == 201, response.text
    return response.json()
