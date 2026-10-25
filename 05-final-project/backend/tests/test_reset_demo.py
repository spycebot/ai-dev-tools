"""scripts/reset_demo.py: the nightly reset of the public staging demo."""

from app.models import CardCreate
from app.seed import SEED_CARDS
from scripts import reset_demo


def test_reset_restores_exactly_the_seed_cards(store):
    store.create_card(CardCreate(title="written by a reviewer"))
    store.create_card(CardCreate(title="another one", column="done"))
    assert reset_demo.reset(store) == 2
    assert sorted(c.title for c in store.list_cards()) == sorted(c["title"] for c in SEED_CARDS)


def test_reset_of_an_edited_seed_board(store):
    reset_demo.reset(store)  # the seed set
    first = store.list_cards()[0]
    store.delete_card(first.id)
    reset_demo.reset(store)
    assert len(store.list_cards()) == len(SEED_CARDS)


def test_refuses_outside_staging(monkeypatch, capsys):
    for value in ("deployment.environment.name=prod,service.version=x", "", None):
        if value is None:
            monkeypatch.delenv("OTEL_RESOURCE_ATTRIBUTES", raising=False)
        else:
            monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", value)
        assert reset_demo.main() == 2
    assert "refusing" in capsys.readouterr().err
