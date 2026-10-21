// Pure board logic used by App.jsx: grouping cards into columns, and working
// out where a drag-and-drop lands. No React, no network, so it can be unit
// tested directly (see board.test.js). The server stays the authority on
// positions: App sends the result to `moveCard` and replaces its state with
// the list the server returns.

import { COLUMNS } from "./api/cards";

/** Group cards by column, each column sorted by position. */
export function groupByColumn(cards) {
  const grouped = Object.fromEntries(COLUMNS.map((key) => [key, []]));
  for (const card of cards) {
    grouped[card.column]?.push(card);
  }
  for (const key of COLUMNS) {
    grouped[key].sort((a, b) => a.position - b.position);
  }
  return grouped;
}

/**
 * Where a dragged card should go. `overId` is what it was dropped on: a
 * column id (append to that column) or another card's id (take that card's
 * place). Returns `{ column, position }`, or null when the drop changes
 * nothing (no target, unknown card, or the same spot).
 */
export function planMove(cards, activeId, overId) {
  // dnd-kit reports the dragged card itself as `over` when it's released
  // over its own slot. Without this check it isn't found among its siblings
  // and would be appended to the end of its column.
  if (overId == null || overId === activeId) return null;
  const active = cards.find((c) => c.id === activeId);
  if (!active) return null;

  const overIsColumn = COLUMNS.includes(overId);
  const column = overIsColumn ? overId : cards.find((c) => c.id === overId)?.column;
  if (!column) return null;

  const columns = groupByColumn(cards);
  const siblings = columns[column].filter((c) => c.id !== activeId);
  let position = siblings.length;
  if (!overIsColumn) {
    const i = siblings.findIndex((c) => c.id === overId);
    if (i !== -1) position = i;
  }

  const unchanged =
    column === active.column &&
    position === columns[column].findIndex((c) => c.id === activeId);
  return unchanged ? null : { column, position };
}

/**
 * The board as it should look right after a move, before the server
 * answers: the card is placed in its new column and that column's positions
 * are renumbered from 0.
 */
export function applyMove(cards, activeId, { column, position }) {
  const active = cards.find((c) => c.id === activeId);
  const siblings = groupByColumn(cards)[column].filter((c) => c.id !== activeId);
  siblings.splice(position, 0, { ...active, column });
  const others = cards.filter((c) => c.id !== activeId && c.column !== column);
  return [...others, ...siblings.map((c, i) => ({ ...c, position: i }))];
}
