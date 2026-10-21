// A tiny fetch stub for tests: routes "METHOD /path" to canned responses
// and records every call, so tests can assert on what the app sent.
import { vi } from "vitest";

/** A Response-like object; `body` undefined means no JSON body. */
export function reply(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => {
      if (body === undefined) throw new SyntaxError("no body");
      return body;
    },
  };
}

/**
 * Install a fetch stub. `routes` maps "METHOD /path" to a reply, or to a
 * function (call) => reply for dynamic answers. Unknown routes get a 404.
 */
export function stubFetch(routes) {
  const calls = [];
  const fetch = vi.fn(async (url, options = {}) => {
    const method = options.method ?? "GET";
    const call = {
      method,
      url,
      options,
      body: options.body ? JSON.parse(options.body) : undefined,
    };
    calls.push(call);
    const route = routes[`${method} ${url}`];
    if (route === undefined) return reply(404, { detail: "Not Found" });
    return typeof route === "function" ? route(call) : route;
  });
  vi.stubGlobal("fetch", fetch);
  return { fetch, calls };
}
