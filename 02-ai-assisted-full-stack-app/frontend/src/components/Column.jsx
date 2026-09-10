import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import CardItem from "./CardItem";

export default function Column({ id, title, cards, onAddCard, onEditCard, onDeleteCard }) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <section className="column">
      <header className="column-header">
        <h2>{title}</h2>
        <span className="column-count" aria-label={`${cards.length} cards`}>
          {cards.length}
        </span>
      </header>

      <div ref={setNodeRef} className={`column-body${isOver ? " column-body--drag-over" : ""}`}>
        <SortableContext items={cards.map((c) => c.id)} strategy={verticalListSortingStrategy}>
          {cards.length === 0 && <p className="column-empty">No cards yet.</p>}
          {cards.map((card) => (
            <CardItem
              key={card.id}
              card={card}
              onEdit={() => onEditCard(card)}
              onDelete={() => onDeleteCard(card.id)}
            />
          ))}
        </SortableContext>
      </div>

      <button type="button" className="add-card-btn" onClick={onAddCard}>
        + Add card
      </button>
    </section>
  );
}
