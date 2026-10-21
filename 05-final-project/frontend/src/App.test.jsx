// The whole app against a stubbed backend: session check, login, loading
// the board, create/delete, and dropping back to login when a session
// expires. Drag-and-drop itself is covered by board.test.js (dnd-kit's
// pointer sensors don't run in jsdom).
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import App from "./App";
import { reply, stubFetch } from "./test/fetch";

const CARDS = [
  { id: "1", title: "Second", description: "", due_date: null, priority: "low", column: "todo", position: 1 },
  { id: "2", title: "First", description: "", due_date: null, priority: "high", column: "todo", position: 0 },
  { id: "3", title: "Doing", description: "", due_date: null, priority: "medium", column: "in_progress", position: 0 },
];

const column = (name) => screen.getByRole("heading", { name, level: 2 }).closest("section");
const titlesIn = (name) =>
  within(column(name)).queryAllByRole("heading", { level: 3 }).map((h) => h.textContent);

describe("App", () => {
  it("shows the login screen when there is no session", async () => {
    stubFetch({ "GET /api/session": reply(200, { authenticated: false }) });
    render(<App />);
    expect(await screen.findByLabelText("Password")).toBeInTheDocument();
  });

  it("logs in, then loads the board with cards in column order", async () => {
    const { calls } = stubFetch({
      "GET /api/session": reply(200, { authenticated: false }),
      "POST /api/login": reply(200, { authenticated: true }),
      "GET /api/cards": reply(200, CARDS),
    });
    render(<App />);
    await userEvent.type(await screen.findByLabelText("Password"), "secret{Enter}");

    expect(await screen.findByRole("heading", { name: "To Do" })).toBeInTheDocument();
    expect(titlesIn("To Do")).toEqual(["First", "Second"]);
    expect(titlesIn("In Progress")).toEqual(["Doing"]);
    expect(within(column("Done")).getByText("No cards yet.")).toBeInTheDocument();
    expect(calls.map((c) => `${c.method} ${c.url}`)).toEqual([
      "GET /api/session",
      "POST /api/login",
      "GET /api/cards",
    ]);
  });

  it("adds a card to the column it was created from", async () => {
    const { calls } = stubFetch({
      "GET /api/session": reply(200, { authenticated: true }),
      "GET /api/cards": reply(200, CARDS),
      "POST /api/cards": ({ body }) =>
        reply(201, { ...body, id: "4", position: 0 }),
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Done" });

    await user.click(within(column("Done")).getByRole("button", { name: "+ Add card" }));
    await user.type(screen.getByLabelText("Title"), "Celebrate");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await within(column("Done")).findByText("Celebrate")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "New card" })).not.toBeInTheDocument();
    expect(calls.at(-1).body).toMatchObject({ title: "Celebrate", column: "done" });
  });

  it("removes a card after a confirmed delete", async () => {
    stubFetch({
      "GET /api/session": reply(200, { authenticated: true }),
      "GET /api/cards": reply(200, CARDS),
      "DELETE /api/cards/3": reply(204),
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Doing");

    const doing = within(column("In Progress"));
    await user.click(doing.getByRole("button", { name: "Delete card" }));
    await user.click(doing.getByRole("button", { name: "Yes" }));

    expect(await within(column("In Progress")).findByText("No cards yet.")).toBeInTheDocument();
  });

  it("shows an error banner and keeps the card when a delete fails", async () => {
    stubFetch({
      "GET /api/session": reply(200, { authenticated: true }),
      "GET /api/cards": reply(200, CARDS),
      "DELETE /api/cards/3": reply(500, { detail: "Database unavailable" }),
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Doing");

    const doing = within(column("In Progress"));
    await user.click(doing.getByRole("button", { name: "Delete card" }));
    await user.click(doing.getByRole("button", { name: "Yes" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Database unavailable");
    expect(titlesIn("In Progress")).toEqual(["Doing"]);
  });

  it("returns to the login screen with a message when the session expires", async () => {
    stubFetch({
      "GET /api/session": reply(200, { authenticated: true }),
      "GET /api/cards": reply(200, CARDS),
      "DELETE /api/cards/3": reply(401, { detail: "Not authenticated" }),
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Doing");

    const doing = within(column("In Progress"));
    await user.click(doing.getByRole("button", { name: "Delete card" }));
    await user.click(doing.getByRole("button", { name: "Yes" }));

    expect(await screen.findByText("Your session expired. Please log in again.")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("logs out back to the login screen", async () => {
    const { calls } = stubFetch({
      "GET /api/session": reply(200, { authenticated: true }),
      "GET /api/cards": reply(200, CARDS),
      "POST /api/logout": reply(200, { authenticated: false }),
    });
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("button", { name: "Log out" }));
    expect(await screen.findByLabelText("Password")).toBeInTheDocument();
    expect(calls.at(-1).url).toBe("/api/logout");
  });
});
