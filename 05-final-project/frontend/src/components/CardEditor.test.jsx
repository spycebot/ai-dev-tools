import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import CardEditor from "./CardEditor";

function setup(props = {}) {
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  const onCancel = vi.fn();
  render(
    <CardEditor mode="create" defaultColumn="in_progress" onSubmit={onSubmit} onCancel={onCancel} {...props} />
  );
  return { user: userEvent.setup(), onSubmit, onCancel };
}

describe("CardEditor", () => {
  it("requires a title and does not submit without one", async () => {
    const { user, onSubmit } = setup();
    await user.type(screen.getByLabelText("Title"), "   ");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByText("Title is required.")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("creates a card in the column it was opened from, with trimmed text", async () => {
    const { user, onSubmit } = setup();
    expect(screen.getByRole("heading", { name: "New card" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Title"), "  Ship it  ");
    await user.type(screen.getByLabelText("Description"), " notes ");
    await user.selectOptions(screen.getByLabelText("Priority"), "high");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).toHaveBeenCalledWith({
      title: "Ship it",
      description: "notes",
      due_date: null,
      priority: "high",
      column: "in_progress",
    });
  });

  it("edits an existing card without sending a column", async () => {
    const card = { id: "7", title: "Old", description: "d", due_date: "2026-10-30", priority: "low" };
    const { user, onSubmit } = setup({ mode: "edit", card });
    expect(screen.getByRole("heading", { name: "Edit card" })).toBeInTheDocument();
    expect(screen.getByLabelText("Due date")).toHaveValue("2026-10-30");
    const title = screen.getByLabelText("Title");
    await user.clear(title);
    await user.type(title, "New");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).toHaveBeenCalledWith({
      title: "New",
      description: "d",
      due_date: "2026-10-30",
      priority: "low",
    });
  });

  it("stays open with the input kept when saving fails", async () => {
    const { user, onSubmit } = setup();
    onSubmit.mockRejectedValue(new Error("server down"));
    await user.type(screen.getByLabelText("Title"), "Keep me");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByLabelText("Title")).toHaveValue("Keep me");
    expect(screen.getByRole("button", { name: "Save" })).toBeEnabled();
  });

  it("cancels from the button or the backdrop, but not from inside the form", async () => {
    const { user, onCancel } = setup();
    await user.click(screen.getByLabelText("Title"));
    expect(onCancel).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledOnce();
    await user.click(document.querySelector(".modal-overlay"));
    expect(onCancel).toHaveBeenCalledTimes(2);
  });
});
