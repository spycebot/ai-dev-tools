import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

const PRIORITY_LABELS = { low: "Low", medium: "Medium", high: "High" };

function isOverdue(card) {
  if (!card.due_date || card.column === "done") return false;
  const due = new Date(`${card.due_date}T23:59:59`);
  return due.getTime() < Date.now();
}

export default function CardItem({ card, onEdit, onDelete }) {
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: card.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  const overdue = isOverdue(card);

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={`card${overdue ? " card--overdue" : ""}${isDragging ? " card--dragging" : ""}`}
      {...attributes}
    >
      <button type="button" className="card-drag-handle" aria-label="Drag to move card" {...listeners}>
        ⠿
      </button>

      <div className="card-content" onClick={onEdit} role="button" tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" ? onEdit() : null)}>
        <h3 className="card-title">{card.title}</h3>
        {card.description && <p className="card-description">{card.description}</p>}
        <div className="card-meta">
          <span className={`priority-badge priority-${card.priority}`}>
            {PRIORITY_LABELS[card.priority] ?? card.priority}
          </span>
          {card.due_date && (
            <span className={`due-date${overdue ? " due-date--overdue" : ""}`}>
              {overdue ? "Overdue " : "Due "}
              {card.due_date}
            </span>
          )}
        </div>
      </div>

      {confirmingDelete ? (
        <div className="confirm-delete">
          <span>Delete?</span>
          <button type="button" className="confirm-yes" onClick={onDelete}>
            Yes
          </button>
          <button type="button" className="confirm-no" onClick={() => setConfirmingDelete(false)}>
            No
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="delete-btn"
          aria-label="Delete card"
          onClick={() => setConfirmingDelete(true)}
        >
          ✕
        </button>
      )}
    </article>
  );
}
