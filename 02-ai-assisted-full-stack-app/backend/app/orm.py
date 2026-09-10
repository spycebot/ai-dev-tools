"""SQLAlchemy ORM model for a card.

`priority` and `column` are stored as plain strings (not a DB `ENUM` type):
the Pydantic `Card` model validates them on the way out, and a string column
behaves identically on SQLite and PostgreSQL. The physical column names
`board_column` / `sort_position` sidestep `COLUMN` and `POSITION` being
reserved words in some dialects.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CardRow(Base):
    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    column: Mapped[str] = mapped_column("board_column", String(16), nullable=False)
    position: Mapped[int] = mapped_column("sort_position", Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
