"""Reset the staging board to the seed cards: the public demo's nightly reset.

Staging doubles as the reviewers' demo, with a published password (README
"For reviewers"), so anyone can change its board. Once a day
`.github/workflows/demo-reset.yml` runs `deploy.sh reset-demo staging`,
which runs this inside the staging container:

    python -m scripts.reset_demo          # in the container, from /app

It deletes every card and recreates the seed set (`app/seed.py`). It refuses
to run anywhere but staging: it checks the environment name that
docker-compose.server.yml sets for OpenTelemetry, which the env files can't
change, and deploy.sh refuses `reset-demo prod` as well.
"""

from __future__ import annotations

import os
import sys

from app.seed import seed_if_empty
from app.store import CardStore

STAGING = "deployment.environment.name=staging"


def reset(store: CardStore) -> int:
    """Delete every card, then reseed. Returns how many cards were deleted."""
    cards = store.list_cards()
    for card in cards:
        store.delete_card(card.id)
    seed_if_empty(store)
    return len(cards)


def main() -> int:
    attributes = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "").split(",")
    if STAGING not in attributes:
        print("reset_demo: refusing, this is not the staging container", file=sys.stderr)
        return 2
    from app.main import _default_store

    deleted = reset(_default_store())
    print(f"demo reset: deleted {deleted} cards, restored the seed set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
