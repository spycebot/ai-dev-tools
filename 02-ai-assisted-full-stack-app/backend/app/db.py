"""Database engine and session plumbing.

Kept deliberately thin and dialect-agnostic: the app only ever names a
`DATABASE_URL`, so pointing it at PostgreSQL later is a config change plus a
driver install (`uv add psycopg`), with no application code touched.
"""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

# Dev default: a file next to the backend package. Override with the env var,
# e.g. DATABASE_URL=postgresql+psycopg://user:pass@host/card_catalog
DEFAULT_DATABASE_URL = "sqlite:///./card_catalog.db"

_IN_MEMORY_SQLITE = {"sqlite://", "sqlite:///:memory:"}


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def make_engine(url: str | None = None) -> Engine:
    url = url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if url in _IN_MEMORY_SQLITE:
            # A pure in-memory database is scoped to its connection, so every
            # pool checkout would otherwise get a fresh, empty schema. Pin one
            # connection for the life of the engine.
            return create_engine(
                url, connect_args=connect_args, poolclass=StaticPool
            )
        return create_engine(url, connect_args=connect_args)

    return create_engine(url)


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    """Create any missing tables. Safe to call on every startup."""
    # Import for the side effect of registering models on Base.metadata.
    from app import orm  # noqa: F401

    Base.metadata.create_all(engine)
