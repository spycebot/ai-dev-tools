"""SQLAlchemy-store behaviour that the in-memory store can't have: data that
outlives the process, and seeding that only happens once.
"""

from app.db import init_db, make_engine, make_session_factory
from app.models import CardCreate, CardMove, CardUpdate
from app.seed import SEED_CARDS, seed_if_empty
from app.sqlalchemy_store import SqlAlchemyCardStore


def _store_on(path):
    engine = make_engine(f"sqlite:///{path}")
    init_db(engine)
    return SqlAlchemyCardStore(make_session_factory(engine))


def test_data_survives_a_new_store_on_the_same_file(tmp_path):
    db = tmp_path / "catalog.db"

    first = _store_on(db)
    created = first.create_card(CardCreate(title="persist me", column="done"))
    first.update_card(created.id, CardUpdate(description="still here"))

    # A brand-new store object, new engine, same file.
    reopened = _store_on(db)
    cards = reopened.list_cards()

    assert [c.id for c in cards] == [created.id]
    assert cards[0].title == "persist me"
    assert cards[0].description == "still here"
    assert cards[0].column.value == "done"


def test_seed_if_empty_only_seeds_once(tmp_path):
    db = tmp_path / "catalog.db"

    store = _store_on(db)
    seed_if_empty(store)
    assert len(store.list_cards()) == len(SEED_CARDS)

    store.delete_card(store.list_cards()[0].id)
    seed_if_empty(_store_on(db))  # DB is non-empty now → no-op

    assert len(_store_on(db).list_cards()) == len(SEED_CARDS) - 1


def test_move_persists(tmp_path):
    db = tmp_path / "catalog.db"
    store = _store_on(db)

    a = store.create_card(CardCreate(title="a", column="todo"))
    b = store.create_card(CardCreate(title="b", column="todo"))
    store.move_card(b.id, CardMove(column="todo", position=0))

    reopened = _store_on(db)
    todo = [c for c in reopened.list_cards() if c.column.value == "todo"]
    assert [c.id for c in todo] == [b.id, a.id]
    assert [c.position for c in todo] == [0, 1]
