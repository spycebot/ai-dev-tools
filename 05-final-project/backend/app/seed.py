"""Seed cards for a fresh board.

Mirrors the frontend prototype's seed set (`frontend/src/api/cards.js`) so the
board looks the same on first run whichever store is behind it. `seed_if_empty`
is called on startup and by the tests; it only writes when the store has no
cards, so it's a no-op on a database that already has data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.models import CardCreate

if TYPE_CHECKING:
    from app.store import CardStore

SEED_CARDS: list[dict] = [
    {
        "title": "Welcome to Card Catalog",
        "description": (
            "This is a sample card. Drag it to another column, edit it, or "
            "delete it to get started."
        ),
        "priority": "medium",
        "column": "todo",
    },
    {
        "title": "Try dragging a card",
        "description": (
            "Cards can be dragged between columns and reordered within a column."
        ),
        "priority": "low",
        "column": "todo",
    },
    {
        "title": "Overdue example",
        "description": (
            "Cards with a past due date that aren't Done are flagged as overdue."
        ),
        "due_date": "2026-01-01",
        "priority": "high",
        "column": "in_progress",
    },
    {
        "title": "Finished task example",
        "description": "This is what a completed card looks like.",
        "priority": "medium",
        "column": "done",
    },
]


def seed_if_empty(store: "CardStore") -> None:
    """Populate `store` with the seed cards, but only if it's currently empty."""
    if store.list_cards():
        return
    for entry in SEED_CARDS:
        store.create_card(CardCreate(**entry))
