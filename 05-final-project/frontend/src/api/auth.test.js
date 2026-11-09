import { describe, expect, it, vi } from "vitest";
import { reply, stubFetch } from "../test/fetch";
import { getSession, login, logout } from "./auth";

describe("auth API client", () => {
  it("posts the password as JSON with the session cookie", async () => {
    const { calls } = stubFetch({ "POST /api/login": reply(200, { authenticated: true }) });
    await login("correct horse");
    expect(calls[0].body).toEqual({ password: "correct horse" });
    expect(calls[0].options.credentials).toBe("same-origin");
  });

  it("rejects with the server's message on a wrong password or lockout", async () => {
    stubFetch({ "POST /api/login": reply(401, { detail: "Incorrect password" }) });
    await expect(login("nope")).rejects.toThrow("Incorrect password");

    stubFetch({ "POST /api/login": reply(429, { detail: "Too many attempts. Try again in a few minutes." }) });
    await expect(login("nope")).rejects.toThrow("Too many attempts");
  });

  it("reports the session state, treating any failure as logged out", async () => {
    const loggedIn = { authenticated: true, authRequired: true };
    const loggedOut = { authenticated: false, authRequired: true };
    stubFetch({ "GET /api/session": reply(200, { authenticated: true, auth_required: true }) });
    await expect(getSession()).resolves.toEqual(loggedIn);

    stubFetch({ "GET /api/session": reply(200, { authenticated: false }) });
    await expect(getSession()).resolves.toEqual(loggedOut);

    stubFetch({ "GET /api/session": reply(500) });
    await expect(getSession()).resolves.toEqual(loggedOut);

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(getSession()).resolves.toEqual(loggedOut);
  });

  it("reports a deployment without a password", async () => {
    stubFetch({ "GET /api/session": reply(200, { authenticated: true, auth_required: false }) });
    await expect(getSession()).resolves.toEqual({ authenticated: true, authRequired: false });
  });

  it("never throws on logout, even offline", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(logout()).resolves.toBeUndefined();
  });
});
