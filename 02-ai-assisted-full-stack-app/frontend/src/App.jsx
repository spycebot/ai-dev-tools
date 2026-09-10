import { useEffect, useMemo, useState } from "react";
import { DndContext, PointerSensor, closestCorners, useSensor, useSensors } from "@dnd-kit/core";
import { COLUMNS, createCard, deleteCard, getCards, moveCard, updateCard } from "./api/cards";
import Column from "./components/Column";
import CardEditor from "./components/CardEditor";
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

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  useEffect(() => {
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
  }, []);

  const columns = useMemo(() => {
    const grouped = { todo: [], in_progress: [], done: [] };
    for (const card of cards) {
      grouped[card.column]?.push(card);
    }
    for (const key of COLUMNS) {
      grouped[key].sort((a, b) => a.position - b.position);
    }
    return grouped;
  }, [cards]);

  function findCard(id) {
    return cards.find((c) => c.id === id);
  }

  async function handleDragEnd(event) {
    const { active, over } = event;
    if (!over) return;

    const activeCard = findCard(active.id);
    if (!activeCard) return;

    const overIsColumn = COLUMNS.includes(over.id);
    const destColumn = overIsColumn ? over.id : findCard(over.id)?.column;
    if (!destColumn) return;

    const destSiblings = columns[destColumn].filter((c) => c.id !== active.id);
    const destIndex = overIsColumn
      ? destSiblings.length
      : (() => {
          const i = destSiblings.findIndex((c) => c.id === over.id);
          return i === -1 ? destSiblings.length : i;
        })();

    if (destColumn === activeCard.column && destIndex === columns[destColumn].findIndex((c) => c.id === active.id)) {
      return; // dropped in the same spot
    }

    // Optimistic local update so the drag feels instant.
    setCards((prev) => {
      const withoutActive = prev.filter((c) => c.id !== active.id);
      const others = withoutActive.filter((c) => c.column !== destColumn);
      const newDest = [...destSiblings];
      newDest.splice(destIndex, 0, { ...activeCard, column: destColumn });
      const withPositions = newDest.map((c, i) => ({ ...c, position: i }));
      return [...others, ...withPositions];
    });

    try {
      const updated = await moveCard(active.id, { column: destColumn, position: destIndex });
      setCards(updated);
    } catch {
      setError("Couldn't save that move. Please try again.");
    }
  }

  async function handleCreate(values) {
    const card = await createCard(values);
    setCards((prev) => [...prev, card]);
    setEditing(null);
  }

  async function handleUpdate(id, values) {
    const updated = await updateCard(id, values);
    setCards((prev) => prev.map((c) => (c.id === id ? updated : c)));
    setEditing(null);
  }

  async function handleDelete(id) {
    await deleteCard(id);
    setCards((prev) => prev.filter((c) => c.id !== id));
  }

  if (loading) {
    return <div className="loading-screen">Loading Card Catalog…</div>;
  }

  return (
    <div className="app">
      <header className="app-header">
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
