// Auth client for Card Catalog's single shared password.
//
// The backend issues a signed, httpOnly session cookie on a successful
// `/api/login` and reads it back on every `/api/cards*` request — this
// module never sees the token itself, it just calls the three auth
// endpoints and lets the browser carry the cookie.

const LOGIN_URL = "/api/login";
const LOGOUT_URL = "/api/logout";
const SESSION_URL = "/api/session";

async function errorMessage(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // no JSON body — fall through to the generic message
  }
  return `Request failed (${response.status})`;
}

/** Log in with the shared password. Throws on failure (wrong password, rate limit, ...). */
export async function login(password) {
  const response = await fetch(LOGIN_URL, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
}

/** Clear the session cookie. Never throws — logging out always "succeeds" locally. */
export async function logout() {
  try {
    await fetch(LOGOUT_URL, { method: "POST", credentials: "same-origin" });
  } catch {
    // Best-effort; the caller clears local state regardless.
  }
}

const LOGGED_OUT = { authenticated: false, authRequired: true };

/**
 * Whether the current session cookie (if any) is still valid, and whether
 * this deployment asks for a password at all (the public staging demo
 * doesn't). Any failure reads as logged out.
 */
export async function getSession() {
  try {
    const response = await fetch(SESSION_URL, { credentials: "same-origin" });
    if (!response.ok) return LOGGED_OUT;
    const body = await response.json();
    return {
      authenticated: Boolean(body.authenticated),
      authRequired: body.auth_required !== false,
    };
  } catch {
    return LOGGED_OUT;
  }
}
