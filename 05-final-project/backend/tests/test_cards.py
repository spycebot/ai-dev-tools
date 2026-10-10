"""Behavioural tests for the Card Catalog API.

Written before the implementation (TDD), per `_docs/specs.md` §8.
"""

from tests.conftest import make_card

CARD_FIELDS = {
    "id",
    "title",
    "description",
    "due_date",
    "priority",
    "column",
    "position",
    "created_at",
    "updated_at",
}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# -- listing --------------------------------------------------------------


def test_list_empty(client):
    response = client.get("/api/cards")
    assert response.status_code == 200
    assert response.json() == []


def test_list_seeded_is_ordered(seeded_client):
    cards = seeded_client.get("/api/cards").json()
    assert len(cards) == 4
    # todo (x2), then in_progress, then done — each block position-ordered.
    assert [c["column"] for c in cards] == [
        "todo",
        "todo",
        "in_progress",
        "done",
    ]
    todo = [c for c in cards if c["column"] == "todo"]
    assert [c["position"] for c in todo] == [0, 1]


# -- creation -----------------------------------------------------------


def test_create_minimal_applies_defaults(client):
    card = make_card(client, title="  Buy milk  ")
    assert set(card) == CARD_FIELDS
    assert card["title"] == "Buy milk"  # trimmed
    assert card["description"] == ""
    assert card["due_date"] is None
    assert card["priority"] == "medium"
    assert card["column"] == "todo"
    assert card["position"] == 0
    assert card["created_at"] == card["updated_at"]


def test_create_appends_to_end_of_column(client):
    first = make_card(client, column="todo")
    second = make_card(client, column="todo")
    third = make_card(client, column="in_progress")
    assert first["position"] == 0
    assert second["position"] == 1
    assert third["position"] == 0  # independent per column


def test_create_with_all_fields(client):
    card = make_card(
        client,
        title="Ship it",
        description="the whole thing",
        due_date="2026-12-31",
        priority="high",
        column="in_progress",
    )
    assert card["due_date"] == "2026-12-31"
    assert card["priority"] == "high"
    assert card["column"] == "in_progress"


def test_create_blank_title_is_rejected(client):
    assert client.post("/api/cards", json={"title": "   "}).status_code == 422


def test_create_missing_title_is_rejected(client):
    assert client.post("/api/cards", json={}).status_code == 422


def test_create_bad_enum_is_rejected(client):
    resp = client.post("/api/cards", json={"title": "x", "priority": "urgent"})
    assert resp.status_code == 422


# -- retrieval --------------------------------------------------------


def test_get_card(client):
    created = make_card(client)
    fetched = client.get(f"/api/cards/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_get_unknown_card_is_404(client):
    resp = client.get("/api/cards/does-not-exist")
    assert resp.status_code == 404


# -- updates ---------------------------------------------------------


def test_update_changes_fields_and_touches_timestamp(client):
    card = make_card(client, title="old", priority="low")
    resp = client.patch(
        f"/api/cards/{card['id']}",
        json={"title": "new", "priority": "high"},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["title"] == "new"
    assert updated["priority"] == "high"
    assert updated["created_at"] == card["created_at"]
    assert updated["updated_at"] >= card["updated_at"]


def test_update_omitted_fields_are_untouched(client):
    card = make_card(client, description="keep me", priority="high")
    updated = client.patch(
        f"/api/cards/{card['id']}", json={"title": "renamed"}
    ).json()
    assert updated["description"] == "keep me"
    assert updated["priority"] == "high"


def test_update_can_clear_due_date_with_null(client):
    card = make_card(client, due_date="2026-01-01")
    updated = client.patch(
        f"/api/cards/{card['id']}", json={"due_date": None}
    ).json()
    assert updated["due_date"] is None


def test_update_cannot_change_column(client):
    card = make_card(client)
    resp = client.patch(
        f"/api/cards/{card['id']}", json={"column": "done"}
    )
    assert resp.status_code == 422  # extra="forbid"


def test_update_blank_title_is_rejected(client):
    card = make_card(client)
    resp = client.patch(f"/api/cards/{card['id']}", json={"title": "  "})
    assert resp.status_code == 422


def test_update_unknown_card_is_404(client):
    assert client.patch("/api/cards/nope", json={"title": "x"}).status_code == 404


# -- deletion --------------------------------------------------------


def test_delete_removes_card(client):
    card = make_card(client)
    assert client.delete(f"/api/cards/{card['id']}").status_code == 204
    assert client.get(f"/api/cards/{card['id']}").status_code == 404


def test_delete_unknown_card_is_404(client):
    assert client.delete("/api/cards/nope").status_code == 404


def test_delete_resequences_remaining_positions(client):
    a = make_card(client, column="todo")
    b = make_card(client, column="todo")
    c = make_card(client, column="todo")
    assert [a["position"], b["position"], c["position"]] == [0, 1, 2]

    client.delete(f"/api/cards/{b['id']}")

    remaining = {card["id"]: card["position"] for card in client.get("/api/cards").json()}
    assert remaining[a["id"]] == 0
    assert remaining[c["id"]] == 1


# -- move / reorder --------------------------------------------------


def test_move_across_columns_updates_both(client):
    todo_a = make_card(client, column="todo")
    todo_b = make_card(client, column="todo")
    done_x = make_card(client, column="done")

    result = client.post(
        f"/api/cards/{todo_a['id']}/move",
        json={"column": "done", "position": 0},
    )
    assert result.status_code == 200
    by_id = {c["id"]: c for c in result.json()}

    assert by_id[todo_a["id"]]["column"] == "done"
    assert by_id[todo_a["id"]]["position"] == 0
    assert by_id[done_x["id"]]["position"] == 1
    # the gap left behind in "todo" is closed
    assert by_id[todo_b["id"]]["position"] == 0


def test_move_reorders_within_a_column(client):
    a = make_card(client, column="todo")
    b = make_card(client, column="todo")
    c = make_card(client, column="todo")

    result = client.post(
        f"/api/cards/{c['id']}/move",
        json={"column": "todo", "position": 0},
    ).json()
    order = [card["id"] for card in result if card["column"] == "todo"]
    assert order == [c["id"], a["id"], b["id"]]
    assert [card["position"] for card in result if card["column"] == "todo"] == [0, 1, 2]


def test_move_position_past_end_appends(client):
    a = make_card(client, column="todo")
    b = make_card(client, column="in_progress")

    result = client.post(
        f"/api/cards/{a['id']}/move",
        json={"column": "in_progress", "position": 99},
    ).json()
    by_id = {c["id"]: c for c in result}
    assert by_id[a["id"]]["position"] == 1
    assert by_id[b["id"]]["position"] == 0


def test_move_negative_position_is_rejected(client):
    card = make_card(client)
    resp = client.post(
        f"/api/cards/{card['id']}/move",
        json={"column": "todo", "position": -1},
    )
    assert resp.status_code == 422


def test_move_unknown_card_is_404(client):
    resp = client.post(
        "/api/cards/nope/move", json={"column": "done", "position": 0}
    )
    assert resp.status_code == 404
