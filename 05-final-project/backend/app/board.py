"""Pure board-ordering rules, shared by every `CardStore` implementation.

The single board has three fixed columns and every card carries a `position`
within its column. Deciding where a new/moved card lands, and how the
positions of the cards around it shift, is the same regardless of where the
data lives — so it lives here once and both the in-memory and SQLAlchemy
stores call into it. No I/O, no ORM: just `Card` values in, plain data out.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.models import Card, Column

# Left-to-right column order for the board.
COLUMN_ORDER: dict[Column, int] = {
    Column.todo: 0,
    Column.in_progress: 1,
    Column.done: 2,
}


@dataclass(frozen=True)
class Placement:
    """Where a card should sit after an operation."""

    card_id: str
    column: Column
    position: int


def board_sorted(cards: Iterable[Card]) -> list[Card]:
    """All cards ordered by column, then by position within the column."""
    return sorted(cards, key=lambda c: (COLUMN_ORDER[c.column], c.position))


def column_sorted(cards: Iterable[Card], column: Column) -> list[Card]:
    """Cards in one column, in position order."""
    return sorted(
        (c for c in cards if c.column == column), key=lambda c: c.position
    )


def next_position(cards: Iterable[Card], column: Column) -> int:
    """The position a new card appended to `column` should get."""
    return max((c.position for c in cards if c.column == column), default=-1) + 1


def resequence(cards: Iterable[Card], column: Column) -> list[Placement]:
    """Placements that make `column` contiguous from 0, order preserved.

    Only cards whose position actually changes are returned.
    """
    return [
        Placement(card.id, column, position)
        for position, card in enumerate(column_sorted(cards, column))
        if card.position != position
    ]


def plan_move(
    cards: list[Card], card_id: str, column: Column, position: int
) -> list[Placement] | None:
    """Every placement implied by moving `card_id` to `column`/`position`.

    Covers both moving between columns and reordering within one. A position
    past the end of the destination appends. Returns ``None`` if the card
    doesn't exist. The caller is responsible for bumping the moved card's
    ``updated_at``.
    """
    moving = next((c for c in cards if c.id == card_id), None)
    if moving is None:
        return None

    destination = [c for c in column_sorted(cards, column) if c.id != card_id]
    index = min(position, len(destination))
    destination.insert(index, moving)

    placements = [
        Placement(card.id, column, pos)
        for pos, card in enumerate(destination)
    ]

    if moving.column != column:
        source_remaining = [
            c for c in column_sorted(cards, moving.column) if c.id != card_id
        ]
        placements += [
            Placement(card.id, moving.column, pos)
            for pos, card in enumerate(source_remaining)
        ]

    return placements
