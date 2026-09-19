"""Alembic migrations against a real Postgres database.

`app.db.init_db` (`Base.metadata.create_all`) is what SQLite dev/unit tests
use; production and this suite use Alembic instead, so these tests are what
actually proves the migrations are correct — nothing else runs them against
Postgres.
"""

from __future__ import annotations

import pytest
from alembic import command
from sqlalchemy import inspect

from app.db import make_engine
from tests.integration.conftest import alembic_config, run_migrations

pytestmark = pytest.mark.integration


def test_upgrade_head_creates_the_cards_table(postgres_url):
    run_migrations(postgres_url)

    engine = make_engine(postgres_url)
    try:
        inspector = inspect(engine)
        assert "cards" in inspector.get_table_names()

        columns = {col["name"] for col in inspector.get_columns("cards")}
        assert columns == {
            "id",
            "title",
            "description",
            "due_date",
            "priority",
            "board_column",
            "sort_position",
            "created_at",
            "updated_at",
        }

        pk = inspector.get_pk_constraint("cards")
        assert pk["constrained_columns"] == ["id"]
    finally:
        engine.dispose()


def test_downgrade_to_base_drops_the_cards_table(postgres_url):
    run_migrations(postgres_url)
    command.downgrade(alembic_config(postgres_url), "base")

    engine = make_engine(postgres_url)
    try:
        assert "cards" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_upgrade_is_idempotent(postgres_url):
    # A real deploy runs `alembic upgrade head` on every release, including
    # ones where the schema didn't change — must be a safe no-op.
    run_migrations(postgres_url)
    run_migrations(postgres_url)

    engine = make_engine(postgres_url)
    try:
        assert "cards" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
