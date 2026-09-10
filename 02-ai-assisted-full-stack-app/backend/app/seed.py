"""Seed cards for the mock data store.

Mirrors the frontend prototype's seed set (`frontend/src/api/cards.js`) so the
board looks the same whether the UI is talking to localStorage or this backend.
"""

from __future__ import annotations

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
