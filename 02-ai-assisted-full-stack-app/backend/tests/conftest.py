import pytest
from fastapi.testclient import TestClient

from app.db import init_db, make_engine, make_session_factory
from app.main import create_app
from app.seed import seed_if_empty
from app.sqlalchemy_store import SqlAlchemyCardStore
from app.store import InMemoryCardStore

# Every store-level / API test runs twice: once against the in-memory store,
# once against a SQLAlchemy store on a throwaway in-memory SQLite database.
# If the two ever disagree, the suite fails.
STORE_KINDS = ["memory", "sqlalchemy"]


@pytest.fixture(params=STORE_KINDS, ids=STORE_KINDS)
def store(request):
    if request.param == "memory":
        yield InMemoryCardStore(seed=False)
        return

    engine = make_engine("sqlite://")  # in-memory, single connection
    init_db(engine)
    try:
        yield SqlAlchemyCardStore(make_session_factory(engine))
    finally:
        engine.dispose()


@pytest.fixture
def client(store) -> TestClient:
    """A client backed by an empty store."""
    return TestClient(create_app(store))


@pytest.fixture
def seeded_client(store) -> TestClient:
    """A client backed by a store carrying the four seed cards."""
    seed_if_empty(store)
    return TestClient(create_app(store))


def make_card(client: TestClient, **overrides) -> dict:
    """Create a card through the API and return its JSON body."""
    body = {"title": "Task", **overrides}
    response = client.post("/api/cards", json=body)
    assert response.status_code == 201, response.text
    return response.json()
