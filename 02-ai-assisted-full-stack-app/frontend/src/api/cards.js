// Backend client for Card Catalog.
//
// This module is the ONLY place in the frontend that talks to the backend.
// Up to homework step 3 it was a localStorage mock; as of step 4 it makes real
// HTTP calls to the FastAPI service defined in `../../openapi.yaml`.
//
// Requests go to a relative `/api/*` path. In development the Vite dev server
// proxies those to the backend (see `vite.config.js`), so the browser always
// makes same-origin calls and there is no CORS to configure.

const CARDS_URL = "/api/cards";

export const COLUMNS = ["todo", "in_progress", "done"];

/** Pull a human-readable message out of a failed response body. */
async function errorMessage(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      const msg = body.detail.map((d) => d.msg).filter(Boolean).join("; ");
      if (msg) return msg;
    }
  } catch {
    // no JSON body — fall through to the generic message
  }
  return `Request failed (${response.status})`;
}

async function request(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch (cause) {
    throw new Error(
      "Can't reach the server. Is the backend running?",
      { cause }
    );
  }

  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  if (response.status === 204) return undefined;
  return response.json();
}

/** Fetch all cards, ordered by column then position. */
export async function getCards() {
  return request(CARDS_URL);
}

/** Create a new card, appended to the end of its column. */
export async function createCard({
  title,
  description = "",
  due_date = null,
  priority = "medium",
  column = "todo",
}) {
  return request(CARDS_URL, {
    method: "POST",
    body: JSON.stringify({ title, description, due_date, priority, column }),
  });
}

/** Update a card's editable fields (title, description, due_date, priority). */
export async function updateCard(id, updates) {
  return request(`${CARDS_URL}/${id}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

/** Permanently delete a card. */
export async function deleteCard(id) {
  return request(`${CARDS_URL}/${id}`, { method: "DELETE" });
}

/**
 * Move a card to a target column/position (drag-and-drop between or within
 * columns). Returns the full, freshly-ordered card list.
 */
export async function moveCard(id, { column, position }) {
  return request(`${CARDS_URL}/${id}/move`, {
    method: "POST",
    body: JSON.stringify({ column, position }),
  });
}
