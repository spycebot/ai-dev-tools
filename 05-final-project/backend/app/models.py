"""Pydantic schemas for the Card Catalog API.

These mirror the data model in `_docs/specs.md` §4 and the shapes declared in
`openapi.yaml`. `Card` is the wire representation returned to clients;
`CardCreate` / `CardUpdate` / `CardMove` are request bodies.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Column(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


def _require_non_blank(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("must not be blank")
    return trimmed


class Card(BaseModel):
    """A single task card, as returned by the API."""

    id: str
    title: str
    description: str = ""
    due_date: date | None = None
    priority: Priority = Priority.medium
    column: Column
    position: int
    created_at: datetime
    updated_at: datetime


class CardCreate(BaseModel):
    """Body for `POST /api/cards`. Only `title` is required."""

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str = ""
    due_date: date | None = None
    priority: Priority = Priority.medium
    column: Column = Column.todo

    @field_validator("title")
    @classmethod
    def _title_non_blank(cls, value: str) -> str:
        return _require_non_blank(value)


class CardUpdate(BaseModel):
    """Body for `PATCH /api/cards/{id}`.

    Every field is optional. Fields left out of the request are unchanged;
    an explicit ``due_date: null`` clears the due date. `column` is not
    editable here — use the move endpoint.
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    due_date: date | None = None
    priority: Priority | None = None

    @field_validator("title")
    @classmethod
    def _title_non_blank(cls, value: str | None) -> str | None:
        return None if value is None else _require_non_blank(value)


class CardMove(BaseModel):
    """Body for `POST /api/cards/{id}/move`."""

    model_config = ConfigDict(extra="forbid")

    column: Column
    position: int

    @field_validator("position")
    @classmethod
    def _position_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be >= 0")
        return value
