"""Fixtures for the Postgres-backed integration suite.

These tests exercise the real deployment target (PostgreSQL via SQLAlchemy,
schema built by Alembic — not `Base.metadata.create_all`) instead of the
SQLite/in-memory stores the rest of the suite uses. See `docs/testing.md`.

Each test gets its own throwaway database on an ephemeral, single-test-session
Postgres *cluster* — not the box's system `postgresql` service, and not
Docker. `pytest-postgresql` starts that cluster with `initdb`/`postgres`
(already installed alongside the `postgresql` apt package) in a temp
directory and tears it down when the test session ends; nothing here ever
touches a real database on this machine.

The `pg_ctl` binary isn't on `PATH` on Debian/Ubuntu (multiple PostgreSQL
versions can be installed side by side), so its location is configurable via
the `PG_CTL_PATH` environment variable — set this if your `pg_ctl` doesn't
live at the Postgres 17 default below (e.g. a different distro, or a CI
runner with a different bundled version).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pytest_postgresql import factories
from sqlalchemy import Engine

from app.db import make_engine, make_session_factory
from app.main import create_app
from app.sqlalchemy_store import SqlAlchemyCardStore
from tests.conftest import TEST_AUTH_CONFIG, TEST_PASSWORD

_DEFAULT_PG_CTL = "/usr/lib/postgresql/17/bin/pg_ctl"
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_ALEMBIC_INI = os.path.join(_BACKEND_DIR, "alembic.ini")

postgresql_proc = factories.postgresql_proc(
    executable=os.environ.get("PG_CTL_PATH", _DEFAULT_PG_CTL),
)


@pytest.fixture
def postgres_url(postgresql_proc) -> Iterator[str]:
    """A URL for a fresh, empty database on the ephemeral test cluster."""
    # Connect to the cluster's always-present "postgres" bootstrap database
    # to issue CREATE/DROP DATABASE — postgresql_proc.dbname ("tests") is
    # never actually created unless something uses the `postgresql` fixture.
    admin_url = (
        f"postgresql://{postgresql_proc.user}@{postgresql_proc.host}"
        f":{postgresql_proc.port}/postgres"
    )
    dbname = f"test_{uuid.uuid4().hex[:16]}"
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{dbname}"')
    try:
        yield (
            f"postgresql+psycopg://{postgresql_proc.user}@{postgresql_proc.host}"
            f":{postgresql_proc.port}/{dbname}"
        )
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(
                f'DROP DATABASE "{dbname}" WITH (FORCE)'
            )


def alembic_config(url: str) -> Config:
    """An Alembic `Config` pointed at `url`, usable with any `alembic.command`."""
    config = Config(_ALEMBIC_INI)
    config.set_main_option("sqlalchemy.url", url)
    config.set_main_option("script_location", os.path.join(_BACKEND_DIR, "migrations"))
    return config


def run_migrations(url: str) -> None:
    """Run every Alembic migration against `url` (same as a real deploy)."""
    command.upgrade(alembic_config(url), "head")


@pytest.fixture
def migrated_engine(postgres_url) -> Iterator[Engine]:
    """A SQLAlchemy engine on a fresh Postgres database, schema via Alembic."""
    run_migrations(postgres_url)
    engine = make_engine(postgres_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def pg_store(migrated_engine) -> SqlAlchemyCardStore:
    """A `SqlAlchemyCardStore` on a migrated, empty Postgres database."""
    return SqlAlchemyCardStore(make_session_factory(migrated_engine))


@pytest.fixture
def pg_client(pg_store) -> TestClient:
    """A logged-in API client backed by the real Postgres store."""
    client = TestClient(create_app(pg_store, auth_config=TEST_AUTH_CONFIG))
    response = client.post("/api/login", json={"password": TEST_PASSWORD})
    assert response.status_code == 200, response.text
    return client
