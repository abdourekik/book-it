import "server-only";

import { cookies } from "next/headers";

import { api, type User } from "@/lib/api";

/**
 * The signed-in session, stored in an httpOnly cookie.
 *
 * `import "server-only"` at the top is a guard rail: if any client component ever
 * imports this file, the build fails instead of quietly shipping the token-handling
 * code - and potentially the token - to the browser.
 */

const TOKEN_COOKIE = "bookit_session";

// Matches ACCESS_TOKEN_EXPIRE_MINUTES on the backend. If the cookie outlived the token,
// users would appear signed in and then get mysterious 401s.
const MAX_AGE_SECONDS = 30 * 60;

export async function setSession(token: string): Promise<void> {
  const store = await cookies();

  store.set(TOKEN_COOKIE, token, {
    // The whole point: JavaScript cannot read this cookie, so an XSS bug cannot steal
    // the token. The browser attaches it to requests automatically.
    httpOnly: true,
    // Only sent over HTTPS in production. Left off locally because dev is plain http.
    secure: process.env.NODE_ENV === "production",
    // Not sent on cross-site POSTs, which is the basic CSRF defence. "lax" rather than
    // "strict" so following a link from an email still arrives signed in.
    sameSite: "lax",
    path: "/",
    maxAge: MAX_AGE_SECONDS,
  });
}

export async function clearSession(): Promise<void> {
  const store = await cookies();
  store.delete(TOKEN_COOKIE);
}

export async function getSessionToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(TOKEN_COOKIE)?.value;
}

/**
 * The signed-in user, or null.
 *
 * Asks the API rather than decoding the token here. A JWT payload is readable but says
 * who the user *was* at login - the backend re-checks the database on every request, so
 * this reflects deletions and role changes immediately. It also means a token that has
 * expired shows up as signed-out rather than as a stale name in the header.
 */
export async function getCurrentUser(): Promise<User | null> {
  const token = await getSessionToken();
  if (!token) return null;

  try {
    return await api.me(token);
  } catch {
    return null;
  }
}
