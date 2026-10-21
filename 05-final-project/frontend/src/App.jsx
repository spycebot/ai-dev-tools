import { useEffect, useMemo, useState } from "react";
import { DndContext, PointerSensor, closestCorners, useSensor, useSensors } from "@dnd-kit/core";
import { getSession, logout } from "./api/auth";
import { COLUMNS, createCard, deleteCard, getCards, moveCard, setUnauthorizedHandler, updateCard } from "./api/cards";
import { applyMove, groupByColumn, planMove } from "./board";
import Column from "./components/Column";
import CardEditor from "./components/CardEditor";
import Login from "./components/Login";
import "./App.css";

const COLUMN_LABELS = {
  todo: "To Do",
  in_progress: "In Progress",
  done: "Done",
};

export default function App() {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // { mode: 'create' | 'edit', card?, column? }
  const [error, setError] = useState(null);
  // null while the initial session check is in flight; true/false after.
  const [authenticated, setAuthenticated] = useState(null);
  const [loginMessage, setLoginMessage] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  // Any card request that comes back 401 (expired/cleared session) bounces
  // back to the login screen instead of surfacing as a generic error.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setAuthenticated(false);
      setLoginMessage("Your session expired. Please log in again.");
    });
  }, []);

  useEffect(() => {
    getSession().then(setAuthenticated);
  }, []);

  useEffect(() => {
    if (!authenticated) return;
    getCards()
      .then((data) => {
        setCards(data);
      })
      .catch(() => {
        setError("Couldn't load the board. Please refresh to try again.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [authenticated]);

  async function handleLogout() {
    await logout();
    setCards([]);
    setLoginMessage(null);
    setAuthenticated(false);
  }

  const columns = useMemo(() => groupByColumn(cards), [cards]);

  async function handleDragEnd(event) {
    const { active, over } = event;
    const move = planMove(cards, active.id, over?.id);
    if (!move) return; // no target, or dropped in the same spot

    // Optimistic local update so the drag feels instant.
    setCards((prev) => applyMove(prev, active.id, move));

    try {
      const updated = await moveCard(active.id, move);
      setCards(updated);
    } catch (err) {
      setError(err.message ?? "Couldn't save that move. Please try again.");
      // Re-sync with the server so the board doesn't keep the failed optimistic move.
      getCards().then(setCards).catch(() => {});
    }
  }

  async function handleCreate(values) {
    try {
      const card = await createCard(values);
      setCards((prev) => [...prev, card]);
      setEditing(null);
    } catch (err) {
      setError(err.message ?? "Couldn't create that card.");
      throw err; // keep the editor open so the user doesn't lose their input
    }
  }

  async function handleUpdate(id, values) {
    try {
      const updated = await updateCard(id, values);
      setCards((prev) => prev.map((c) => (c.id === id ? updated : c)));
      setEditing(null);
    } catch (err) {
      setError(err.message ?? "Couldn't save that card.");
      throw err;
    }
  }

  async function handleDelete(id) {
    try {
      await deleteCard(id);
      setCards((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      setError(err.message ?? "Couldn't delete that card.");
    }
  }

  if (authenticated === null) {
    return <div className="loading-screen">Loading Card Catalog…</div>;
  }

  if (!authenticated) {
    return (
      <Login
        message={loginMessage}
        onSuccess={() => {
          setLoading(true);
          setAuthenticated(true);
        }}
      />
    );
  }

  if (loading) {
    return <div className="loading-screen">Loading Card Catalog…</div>;
  }

  return (
    <div className="app">
      <header className="app-header">
        <button className="logout-button" onClick={handleLogout}>
          Log out
        </button>
        <h1>Card Catalog</h1>
        <p className="app-subtitle">a mini kanban board</p>
      </header>

      {error && (
        <div className="error-banner" role="alert" onClick={() => setError(null)}>
          {error}
        </div>
      )}

      <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={handleDragEnd}>
        <main className="board">
          {COLUMNS.map((key) => (
            <Column
              key={key}
              id={key}
              title={COLUMN_LABELS[key]}
              cards={columns[key]}
              onAddCard={() => setEditing({ mode: "create", column: key })}
              onEditCard={(card) => setEditing({ mode: "edit", card })}
              onDeleteCard={handleDelete}
            />
          ))}
        </main>
      </DndContext>

      {editing && (
        <CardEditor
          mode={editing.mode}
          card={editing.card}
          defaultColumn={editing.column}
          onCancel={() => setEditing(null)}
          onSubmit={(values) =>
            editing.mode === "create" ? handleCreate(values) : handleUpdate(editing.card.id, values)
          }
        />
      )}
    </div>
  );
}
