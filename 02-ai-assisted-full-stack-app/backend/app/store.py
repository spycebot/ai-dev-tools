"""Data store for the Card Catalog backend.

`CardStore` is the interface the API routes depend on. `InMemoryCardStore` is
the mock implementation used for homework steps 3 and 4 — a plain dict, no
persistence beyond process lifetime. Homework step 5 adds a SQLAlchemy-backed
implementation of the same interface, so `app/main.py` never has to change.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Protocol

from app.models import Card, CardCreate, CardMove, CardUpdate, Column
from app.seed import SEED_CARDS

# Column display / sort order for the single fixed board.
_COLUMN_ORDER: dict[Column, int] = {
    Column.todo: 0,
    Column.in_progress: 1,
    Column.done: 2,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CardStore(Protocol):
    """Everything the API needs from a persistence layer."""

    def list_cards(self) -> list[Card]: ...

    def get_card(self, card_id: str) -> Card | None: ...

    def create_card(self, data: CardCreate) -> Card: ...

    def update_card(self, card_id: str, data: CardUpdate) -> Card | None: ...

    def delete_card(self, card_id: str) -> bool: ...

    def move_card(self, card_id: str, move: CardMove) -> list[Card] | None: ...


class InMemoryCardStore:
    """Mock data store — holds cards in a dict keyed by id."""

    def __init__(self, seed: bool = True) -> None:
        self._cards: dict[str, Card] = {}
        if seed:
            for entry in SEED_CARDS:
                self.create_card(CardCreate(**entry))

    # -- reads -------------------------------------------------------------

    def list_cards(self) -> list[Card]:
        """All cards, ordered by column then position."""
        return sorted(
            self._cards.values(),
            key=lambda c: (_COLUMN_ORDER[c.column], c.position),
        )

    def get_card(self, card_id: str) -> Card | None:
        return self._cards.get(card_id)

    # -- writes ----------------------------------------------------------

    def create_card(self, data: CardCreate) -> Card:
        """Create a card appended to the end of its column."""
        siblings = [c for c in self._cards.values() if c.column == data.column]
        next_position = max((c.position for c in siblings), default=-1) + 1
        timestamp = _now()
        card = Card(
            id=str(uuid.uuid4()),
            title=data.title,
            description=data.description,
            due_date=data.due_date,
            priority=data.priority,
            column=data.column,
            position=next_position,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._cards[card.id] = card
        return card

    def update_card(self, card_id: str, data: CardUpdate) -> Card | None:
        card = self._cards.get(card_id)
        if card is None:
            return None
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return card
        updated = card.model_copy(update={**changes, "updated_at": _now()})
        self._cards[card_id] = updated
        return updated

    def delete_card(self, card_id: str) -> bool:
        card = self._cards.pop(card_id, None)
        if card is None:
            return False
        self._resequence(card.column)
        return True

    def move_card(self, card_id: str, move: CardMove) -> list[Card] | None:
        card = self._cards.get(card_id)
        if card is None:
            return None

        source_column = card.column
        destination = [
            c for c in self._sorted_column(move.column) if c.id != card_id
        ]
        index = min(move.position, len(destination))
        moved = card.model_copy(
            update={"column": move.column, "updated_at": _now()}
        )
        destination.insert(index, moved)

        for position, sibling in enumerate(destination):
            self._cards[sibling.id] = sibling.model_copy(
                update={"position": position}
            )

        if source_column != move.column:
            self._resequence(source_column)

        return self.list_cards()

    # -- helpers -------------------------------------------------------

    def _sorted_column(self, column: Column) -> list[Card]:
        return sorted(
            (c for c in self._cards.values() if c.column == column),
            key=lambda c: c.position,
        )

    def _resequence(self, column: Column) -> None:
        """Make positions in a column contiguous from 0, order preserved."""
        for position, card in enumerate(self._sorted_column(column)):
            if card.position != position:
                self._cards[card.id] = card.model_copy(
                    update={"position": position}
                )
