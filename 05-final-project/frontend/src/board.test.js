import { describe, expect, it } from "vitest";
import { applyMove, groupByColumn, planMove } from "./board";

// todo: a(0) b(1) c(2) · in_progress: d(0) · done: (empty)
const card = (id, column, position) => ({ id, column, position, title: id });
const board = [
  card("c", "todo", 2),
  card("a", "todo", 0),
  card("d", "in_progress", 0),
  card("b", "todo", 1),
];
const ids = (cards) => cards.map((c) => c.id);

describe("groupByColumn", () => {
  it("groups cards into the three columns, each sorted by position", () => {
    const columns = groupByColumn(board);
    expect(ids(columns.todo)).toEqual(["a", "b", "c"]);
    expect(ids(columns.in_progress)).toEqual(["d"]);
    expect(columns.done).toEqual([]);
  });

  it("ignores cards in an unknown column instead of crashing", () => {
    const columns = groupByColumn([...board, card("x", "archived", 0)]);
    expect(Object.keys(columns)).toEqual(["todo", "in_progress", "done"]);
    expect(Object.values(columns).flat()).toHaveLength(4);
  });
});

describe("planMove", () => {
  it("appends to the end when dropped on a column", () => {
    expect(planMove(board, "a", "in_progress")).toEqual({ column: "in_progress", position: 1 });
    expect(planMove(board, "a", "done")).toEqual({ column: "done", position: 0 });
  });

  it("takes the target card's place when dropped on a card in another column", () => {
    expect(planMove(board, "b", "d")).toEqual({ column: "in_progress", position: 0 });
  });

  it("reorders within a column", () => {
    expect(planMove(board, "c", "a")).toEqual({ column: "todo", position: 0 });
    // Moving down: a's siblings are b, c, so dropping on c means index 1.
    expect(planMove(board, "a", "c")).toEqual({ column: "todo", position: 1 });
  });

  it("returns null when nothing would change", () => {
    expect(planMove(board, "b", "b")).toBeNull(); // dropped on itself
    expect(planMove(board, "c", "todo")).toBeNull(); // already last in its column
    expect(planMove(board, "a", undefined)).toBeNull(); // dropped outside the board
    expect(planMove(board, "a", null)).toBeNull();
    expect(planMove(board, "zz", "todo")).toBeNull(); // unknown card
    expect(planMove(board, "a", "zz")).toBeNull(); // unknown target
  });
});

describe("applyMove", () => {
  it("moves the card and renumbers the destination column from 0", () => {
    const after = groupByColumn(applyMove(board, "b", { column: "in_progress", position: 0 }));
    expect(ids(after.in_progress)).toEqual(["b", "d"]);
    expect(after.in_progress.map((c) => c.position)).toEqual([0, 1]);
    expect(after.in_progress[0].column).toBe("in_progress");
    expect(ids(after.todo)).toEqual(["a", "c"]);
  });

  it("reorders within a column without losing or duplicating cards", () => {
    const moved = applyMove(board, "c", { column: "todo", position: 0 });
    expect(moved).toHaveLength(board.length);
    const todo = groupByColumn(moved).todo;
    expect(ids(todo)).toEqual(["c", "a", "b"]);
    expect(todo.map((c) => c.position)).toEqual([0, 1, 2]);
  });

  it("does not mutate the input", () => {
    const snapshot = structuredClone(board);
    applyMove(board, "a", { column: "done", position: 0 });
    expect(board).toEqual(snapshot);
  });
});
