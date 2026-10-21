import { afterEach, describe, expect, it, vi } from "vitest";
import { reply, stubFetch } from "../test/fetch";
import {
  createCard,
  deleteCard,
  getCards,
  moveCard,
  setUnauthorizedHandler,
  updateCard,
} from "./cards";

afterEach(() => setUnauthorizedHandler(() => {}));

describe("cards API client", () => {
  it("lists cards with the session cookie and no JSON content type", async () => {
    const { calls } = stubFetch({ "GET /api/cards": reply(200, [{ id: "1" }]) });
    await expect(getCards()).resolves.toEqual([{ id: "1" }]);
    expect(calls[0].options.credentials).toBe("same-origin");
    expect(calls[0].options.headers).toEqual({});
  });

  it("creates a card with the documented defaults", async () => {
    const { calls } = stubFetch({ "POST /api/cards": reply(201, { id: "9" }) });
    await createCard({ title: "Write tests" });
    expect(calls[0].body).toEqual({
      title: "Write tests",
      description: "",
      due_date: null,
      priority: "medium",
      column: "todo",
    });
    expect(calls[0].options.headers).toEqual({ "Content-Type": "application/json" });
  });

  it("sends update, move and delete to the card's own URL", async () => {
    const { calls } = stubFetch({
      "PATCH /api/cards/42": reply(200, { id: "42" }),
      "POST /api/cards/42/move": reply(200, []),
      "DELETE /api/cards/42": reply(204),
    });
    await updateCard("42", { title: "New" });
    await moveCard("42", { column: "done", position: 3 });
    await expect(deleteCard("42")).resolves.toBeUndefined(); // 204: no body read
    expect(calls.map((c) => `${c.method} ${c.url}`)).toEqual([
      "PATCH /api/cards/42",
      "POST /api/cards/42/move",
      "DELETE /api/cards/42",
    ]);
    expect(calls[0].body).toEqual({ title: "New" });
    expect(calls[1].body).toEqual({ column: "done", position: 3 });
  });

  it("surfaces the server's error detail", async () => {
    stubFetch({ "PATCH /api/cards/1": reply(404, { detail: "Card not found" }) });
    await expect(updateCard("1", {})).rejects.toThrow("Card not found");
  });

  it("joins FastAPI validation errors into one message", async () => {
    stubFetch({
      "POST /api/cards": reply(422, {
        detail: [{ msg: "Field required" }, { msg: "String too long" }],
      }),
    });
    await expect(createCard({ title: "" })).rejects.toThrow("Field required; String too long");
  });

  it("falls back to a generic message when the error has no JSON body", async () => {
    stubFetch({ "GET /api/cards": reply(502) });
    await expect(getCards()).rejects.toThrow("Request failed (502)");
  });

  it("explains a network failure instead of leaking the raw TypeError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(getCards()).rejects.toThrow("Can't reach the server. Is the backend running?");
  });

  it("calls the unauthorized handler on 401, and still rejects", async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    stubFetch({ "GET /api/cards": reply(401, { detail: "Not authenticated" }) });
    await expect(getCards()).rejects.toThrow("Not authenticated");
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("does not call the unauthorized handler for other errors", async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    stubFetch({ "GET /api/cards": reply(500, { detail: "boom" }) });
    await expect(getCards()).rejects.toThrow("boom");
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});
