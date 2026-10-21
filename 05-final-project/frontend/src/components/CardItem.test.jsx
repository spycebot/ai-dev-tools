import { DndContext } from "@dnd-kit/core";
import { SortableContext } from "@dnd-kit/sortable";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import CardItem from "./CardItem";

function renderCard(overrides = {}, handlers = {}) {
  const card = {
    id: "1",
    title: "Pay invoice",
    description: "",
    due_date: null,
    priority: "medium",
    column: "todo",
    position: 0,
    ...overrides,
  };
  const props = { onEdit: vi.fn(), onDelete: vi.fn(), ...handlers };
  render(
    <DndContext>
      <SortableContext items={[card.id]}>
        <CardItem card={card} {...props} />
      </SortableContext>
    </DndContext>
  );
  return props;
}

describe("CardItem", () => {
  it("shows title, description and priority", () => {
    renderCard({ description: "Before Friday", priority: "high" });
    expect(screen.getByRole("heading", { name: "Pay invoice" })).toBeInTheDocument();
    expect(screen.getByText("Before Friday")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  describe("due dates", () => {
    // Freeze "now" at midday on 2026-10-21 (local time).
    const now = new Date(2026, 9, 21, 12, 0, 0);

    it("marks a past due date as overdue", () => {
      vi.useFakeTimers({ now, toFake: ["Date"] });
      renderCard({ due_date: "2026-10-20" });
      expect(screen.getByText(/Overdue/)).toHaveTextContent("Overdue 2026-10-20");
      expect(screen.getByRole("heading").closest("article")).toHaveClass("card--overdue");
    });

    it("is not overdue until the end of the due day", () => {
      vi.useFakeTimers({ now, toFake: ["Date"] });
      renderCard({ due_date: "2026-10-21" });
      expect(screen.getByText(/Due/)).toHaveTextContent("Due 2026-10-21");
      expect(screen.queryByText(/Overdue/)).not.toBeInTheDocument();
    });

    it("never marks a done card as overdue", () => {
      vi.useFakeTimers({ now, toFake: ["Date"] });
      renderCard({ due_date: "2020-01-01", column: "done" });
      expect(screen.queryByText(/Overdue/)).not.toBeInTheDocument();
    });
  });

  it("asks for confirmation before deleting", async () => {
    const user = userEvent.setup();
    const { onDelete } = renderCard();
    await user.click(screen.getByRole("button", { name: "Delete card" }));
    await user.click(screen.getByRole("button", { name: "No" }));
    expect(onDelete).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Delete card" }));
    await user.click(screen.getByRole("button", { name: "Yes" }));
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it("opens the editor on click or Enter", async () => {
    const user = userEvent.setup();
    const { onEdit } = renderCard();
    const content = screen.getByRole("heading").closest("[role=button]");
    await user.click(content);
    content.focus();
    await user.keyboard("{Enter}");
    expect(onEdit).toHaveBeenCalledTimes(2);
  });
});
