"""SQLAlchemy-backed `CardStore` (homework step 5).

Same interface as `InMemoryCardStore`; `app/main.py` doesn't know the
difference. All the "where does a card land" logic is delegated to
`app.board`, so the two stores can't drift apart — the test suite runs against
both.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app import board
from app.models import Card, CardCreate, CardMove, CardUpdate, Column
from app.orm import CardRow


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    """SQLite hands back naive datetimes; treat stored times as UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _to_card(row: CardRow) -> Card:
    return Card(
        id=row.id,
        title=row.title,
        description=row.description,
        due_date=row.due_date,
        priority=row.priority,
        column=row.column,
        position=row.position,
        created_at=_aware(row.created_at),
        updated_at=_aware(row.updated_at),
    )


def _scalar(value):
    """Enum -> its string value; everything else unchanged."""
    return value.value if isinstance(value, Enum) else value


class SqlAlchemyCardStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_cards(self) -> list[Card]:
        with self._session_factory() as session:
            rows = session.scalars(select(CardRow)).all()
        return board.board_sorted([_to_card(r) for r in rows])

    def get_card(self, card_id: str) -> Card | None:
        with self._session_factory() as session:
            row = session.get(CardRow, card_id)
            return _to_card(row) if row is not None else None

    def create_card(self, data: CardCreate) -> Card:
        with self._session_factory() as session, session.begin():
            existing = [
                _to_card(r) for r in session.scalars(select(CardRow)).all()
            ]
            timestamp = _now()
            row = CardRow(
                id=str(uuid.uuid4()),
                title=data.title,
                description=data.description,
                due_date=data.due_date,
                priority=data.priority.value,
                column=data.column.value,
                position=board.next_position(existing, data.column),
                created_at=timestamp,
                updated_at=timestamp,
            )
            session.add(row)
            session.flush()
            return _to_card(row)

    def update_card(self, card_id: str, data: CardUpdate) -> Card | None:
        with self._session_factory() as session, session.begin():
            row = session.get(CardRow, card_id)
            if row is None:
                return None
            changes = data.model_dump(exclude_unset=True)
            for field, value in changes.items():
                setattr(row, field, _scalar(value))
            if changes:
                row.updated_at = _now()
            session.flush()
            return _to_card(row)

    def delete_card(self, card_id: str) -> bool:
        with self._session_factory() as session, session.begin():
            row = session.get(CardRow, card_id)
            if row is None:
                return False
            column = Column(row.column)
            session.delete(row)
            session.flush()
            self._apply(
                session,
                board.resequence(self._load(session), column),
            )
            return True

    def move_card(self, card_id: str, move: CardMove) -> list[Card] | None:
        with self._session_factory() as session, session.begin():
            row = session.get(CardRow, card_id)
            if row is None:
                return None
            placements = board.plan_move(
                self._load(session), card_id, move.column, move.position
            )
            self._apply(session, placements or [])
            row.updated_at = _now()
            session.flush()
            return board.board_sorted(
                [_to_card(r) for r in session.scalars(select(CardRow)).all()]
            )

    # -- helpers -------------------------------------------------------

    @staticmethod
    def _load(session: Session) -> list[Card]:
        return [_to_card(r) for r in session.scalars(select(CardRow)).all()]

    @staticmethod
    def _apply(session: Session, placements: list[board.Placement]) -> None:
        for placement in placements:
            row = session.get(CardRow, placement.card_id)
            row.column = placement.column.value
            row.position = placement.position
