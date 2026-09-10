// Mocked backend for Card Catalog.
//
// This module is the ONLY place in the frontend that talks to "the backend".
// Every function here returns a Promise, matching the shape a real HTTP call
// to the future FastAPI service will have, so that swapping this module out
// for real `fetch()` calls later (homework step 4) does not require changing
// any component code — only this file.
//
// For now, "the backend" is `localStorage`, so data persists across reloads
// even though there is no server yet.

const STORAGE_KEY = "card-catalog:cards";
const SIMULATED_LATENCY_MS = 150;

export const COLUMNS = ["todo", "in_progress", "done"];

const SEED_CARDS = [
  {
    title: "Welcome to Card Catalog",
    description:
      "This is a sample card. Drag it to another column, edit it, or delete it to get started.",
    due_date: null,
    priority: "medium",
    column: "todo",
  },
  {
    title: "Try dragging a card",
    description: "Cards can be dragged between columns and reordered within a column.",
    due_date: null,
    priority: "low",
    column: "todo",
  },
  {
    title: "Overdue example",
    description: "Cards with a past due date that aren't Done are flagged as overdue.",
    due_date: "2026-01-01",
    priority: "high",
    column: "in_progress",
  },
  {
    title: "Finished task example",
    description: "This is what a completed card looks like.",
    due_date: null,
    priority: "medium",
    column: "done",
  },
];

function uuid() {
  // `crypto.randomUUID` only exists in a secure context (HTTPS or localhost).
  // When the app is served over plain HTTP from a bare IP it's undefined, so
  // fall back to `crypto.getRandomValues`, which is available everywhere.
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 10
  const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0"));
  return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex
    .slice(6, 8)
    .join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10, 16).join("")}`;
}

function now() {
  return new Date().toISOString();
}

function loadAll() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    const seeded = SEED_CARDS.map((card, index) => ({
      id: uuid(),
      title: card.title,
      description: card.description ?? "",
      due_date: card.due_date ?? null,
      priority: card.priority ?? "medium",
      column: card.column,
      position: index,
      created_at: now(),
      updated_at: now(),
    }));
    saveAll(seeded);
    return seeded;
  }
  return JSON.parse(raw);
}

function saveAll(cards) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cards));
}

function delay(value) {
  return new Promise((resolve) => setTimeout(() => resolve(value), SIMULATED_LATENCY_MS));
}

function sortByPosition(cards) {
  return [...cards].sort((a, b) => a.position - b.position);
}

function normalizeColumnPositions(cards, column) {
  const inColumn = sortByPosition(cards.filter((c) => c.column === column));
  inColumn.forEach((card, index) => {
    card.position = index;
  });
  return cards;
}

/** Fetch all cards, sorted by column then position. */
export async function getCards() {
  const cards = loadAll();
  return delay(sortByPosition(cards));
}

/** Create a new card, appended to the end of its column. */
export async function createCard({ title, description = "", due_date = null, priority = "medium", column = "todo" }) {
  if (!title || !title.trim()) {
    throw new Error("Title is required");
  }
  const cards = loadAll();
  const inColumn = cards.filter((c) => c.column === column);
  const nextPosition = inColumn.length > 0 ? Math.max(...inColumn.map((c) => c.position)) + 1 : 0;

  const card = {
    id: uuid(),
    title: title.trim(),
    description,
    due_date,
    priority,
    column,
    position: nextPosition,
    created_at: now(),
    updated_at: now(),
  };

  cards.push(card);
  saveAll(cards);
  return delay(card);
}

/** Update a card's editable fields (title, description, due_date, priority). */
export async function updateCard(id, updates) {
  const cards = loadAll();
  const card = cards.find((c) => c.id === id);
  if (!card) {
    throw new Error(`Card ${id} not found`);
  }
  Object.assign(card, updates, { updated_at: now() });
  saveAll(cards);
  return delay(card);
}

/** Permanently delete a card. */
export async function deleteCard(id) {
  const cards = loadAll();
  const remaining = cards.filter((c) => c.id !== id);
  saveAll(remaining);
  return delay(undefined);
}

/**
 * Move a card to a target column/position, e.g. via drag-and-drop.
 * Used both for moving a card between columns and for reordering a card
 * within its current column. Returns the full, freshly-sorted card list.
 */
export async function moveCard(id, { column, position }) {
  const cards = loadAll();
  const card = cards.find((c) => c.id === id);
  if (!card) {
    throw new Error(`Card ${id} not found`);
  }

  const sourceColumn = card.column;
  card.column = column;
  card.updated_at = now();

  // Re-sequence the destination column with this card inserted at `position`.
  const destCards = sortByPosition(cards.filter((c) => c.column === column && c.id !== id));
  destCards.splice(position, 0, card);
  destCards.forEach((c, index) => {
    c.position = index;
  });

  if (sourceColumn !== column) {
    normalizeColumnPositions(cards, sourceColumn);
  }

  saveAll(cards);
  return delay(sortByPosition(cards));
}
