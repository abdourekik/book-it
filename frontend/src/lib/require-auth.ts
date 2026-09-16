import "server-only";

import { redirect } from "next/navigation";

import type { User } from "@/lib/api";
import { getCurrentUser, getSessionToken } from "@/lib/session";

/**
 * Guards for pages that need a signed-in user.
 *
 * Returning the token alongside the user saves every caller a second cookie read, and
 * means the page passes one thing to the API client rather than rebuilding auth headers.
 */

export async function requireUser(): Promise<{ user: User; token: string }> {
  const [user, token] = await Promise.all([getCurrentUser(), getSessionToken()]);

  if (!user || !token) redirect("/login");
  return { user, token };
}

export async function requireOwner(): Promise<{ user: User; token: string }> {
  const session = await requireUser();

  // A customer reaching /dashboard is not an attack, just a wrong turn - send them home
  // rather than showing an error. The API enforces the real rule with a 403 regardless.
  if (session.user.role !== "owner") redirect("/");
  return session;
}
