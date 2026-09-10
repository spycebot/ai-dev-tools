"""Data store interface + the in-memory implementation.

`CardStore` is the interface the API routes depend on. `InMemoryCardStore` is
the original mock (a plain dict, no persistence beyond process lifetime); it
stays as the reference implementation and is still handy for tests. The
SQLAlchemy implementation lives in `app/sqlalchemy_store.py` and satisfies the
same `CardStore` protocol, so `app/main.py` never has to change.

All position/ordering rules are delegated to `app.board` so the two stores
behave identically.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Protocol

from app import board
from app.models import Card, CardCreate, CardMove, CardUpdate
from app.seed import seed_if_empty


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
            seed_if_empty(self)

    # -- reads -----------------------------------------------------------

    def list_cards(self) -> list[Card]:
        return board.board_sorted(self._cards.values())

    def get_card(self, card_id: str) -> Card | None:
        return self._cards.get(card_id)

    # -- writes --------------------------------------------------------

    def create_card(self, data: CardCreate) -> Card:
        timestamp = _now()
        card = Card(
            id=str(uuid.uuid4()),
            title=data.title,
            description=data.description,
            due_date=data.due_date,
            priority=data.priority,
            column=data.column,
            position=board.next_position(self._cards.values(), data.column),
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
        self._apply(board.resequence(self._cards.values(), card.column))
        return True

    def move_card(self, card_id: str, move: CardMove) -> list[Card] | None:
        if card_id not in self._cards:
            return None
        placements = board.plan_move(
            list(self._cards.values()), card_id, move.column, move.position
        )
        self._apply(placements or [])
        moved = self._cards[card_id]
        self._cards[card_id] = moved.model_copy(update={"updated_at": _now()})
        return self.list_cards()

    # -- helpers -----------------------------------------------------

    def _apply(self, placements: list[board.Placement]) -> None:
        for placement in placements:
            card = self._cards[placement.card_id]
            self._cards[placement.card_id] = card.model_copy(
                update={
                    "column": placement.column,
                    "position": placement.position,
                }
            )
