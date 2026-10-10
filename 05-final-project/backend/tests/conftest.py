import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.auth import AuthConfig
from app.db import init_db, make_engine, make_session_factory
from app.main import create_app
from app.seed import seed_if_empty
from app.sqlalchemy_store import SqlAlchemyCardStore
from app.store import InMemoryCardStore

# A fixed, low-cost (fast to hash) test password/config — never used outside
# tests. Card CRUD tests log in once via this and don't otherwise think about
# auth; auth behaviour itself is exercised in test_auth.py.
TEST_PASSWORD = "correct horse battery staple"
TEST_AUTH_CONFIG = AuthConfig(
    password_hash=bcrypt.hashpw(
        TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)
    ).decode(),
    secret_key="test-only-secret-key",
    cookie_secure=False,  # TestClient talks plain HTTP
)

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


def _logged_in(client: TestClient) -> TestClient:
    response = client.post("/api/login", json={"password": TEST_PASSWORD})
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def client(store) -> TestClient:
    """A logged-in client backed by an empty store."""
    return _logged_in(TestClient(create_app(store, auth_config=TEST_AUTH_CONFIG)))


@pytest.fixture
def seeded_client(store) -> TestClient:
    """A logged-in client backed by a store carrying the four seed cards."""
    seed_if_empty(store)
    return _logged_in(TestClient(create_app(store, auth_config=TEST_AUTH_CONFIG)))


def make_card(client: TestClient, **overrides) -> dict:
    """Create a card through the API and return its JSON body."""
    body = {"title": "Task", **overrides}
    response = client.post("/api/cards", json=body)
    assert response.status_code == 201, response.text
    return response.json()
