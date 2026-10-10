import { useState } from "react";

const PRIORITIES = ["low", "medium", "high"];

export default function CardEditor({ mode, card, defaultColumn, onCancel, onSubmit }) {
  const [title, setTitle] = useState(card?.title ?? "");
  const [description, setDescription] = useState(card?.description ?? "");
  const [dueDate, setDueDate] = useState(card?.due_date ?? "");
  const [priority, setPriority] = useState(card?.priority ?? "medium");
  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!title.trim()) {
      setValidationError("Title is required.");
      return;
    }
    setValidationError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        title: title.trim(),
        description: description.trim(),
        due_date: dueDate || null,
        priority,
        ...(mode === "create" ? { column: defaultColumn } : {}),
      });
    } catch {
      // The parent surfaces the error in the board's error banner; keep this
      // form open so the user's input isn't lost.
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <form className="modal card-editor" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>{mode === "create" ? "New card" : "Edit card"}</h2>

        <label>
          Title
          <input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Card title"
          />
        </label>

        <label>
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            placeholder="Details (optional)"
          />
        </label>

        <div className="form-row">
          <label>
            Due date
            <input type="date" value={dueDate ?? ""} onChange={(e) => setDueDate(e.target.value)} />
          </label>

          <label>
            Priority
            <select value={priority} onChange={(e) => setPriority(e.target.value)}>
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p[0].toUpperCase() + p.slice(1)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {validationError && <p className="form-error">{validationError}</p>}

        <div className="form-actions">
          <button type="button" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}
