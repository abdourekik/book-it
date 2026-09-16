"use server";

import { redirect } from "next/navigation";

import { ApiError, api } from "@/lib/api";
import { clearSession, setSession } from "@/lib/session";

import type { FormState } from "./form-state";

/**
 * Server Actions for signing up, signing in, and signing out.
 *
 * "use server" means these functions run on the server even though a client component
 * calls them. That is what keeps the token out of the browser: the form posts here, we
 * call FastAPI, and we write an httpOnly cookie - the browser's JavaScript never sees
 * the token at any point.
 */

function readString(formData: FormData, field: string): string {
  const value = formData.get(field);
  return typeof value === "string" ? value.trim() : "";
}

export async function signupAction(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const email = readString(formData, "email");
  const password = readString(formData, "password");
  const fullName = readString(formData, "full_name");
  const role = readString(formData, "role") === "owner" ? "owner" : "customer";

  if (!email || !password || !fullName) {
    return { error: "Please fill in every field." };
  }

  try {
    await api.signup({ email, password, full_name: fullName, role });
    // Sign them straight in rather than making them type the same details again.
    const token = await api.login({ email, password });
    await setSession(token.access_token);
  } catch (error) {
    return { error: messageFor(error) };
  }

  // redirect() throws internally to unwind the request, so it must sit OUTSIDE the
  // try/catch - inside, the catch block would swallow it and the redirect would never
  // happen. This is the single most common Server Action bug.
  redirect(role === "owner" ? "/dashboard" : "/");
}

export async function loginAction(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const email = readString(formData, "email");
  const password = readString(formData, "password");

  if (!email || !password) {
    return { error: "Please enter your email and password." };
  }

  try {
    const token = await api.login({ email, password });
    await setSession(token.access_token);
  } catch (error) {
    return { error: messageFor(error) };
  }

  redirect("/");
}

export async function logoutAction(): Promise<void> {
  await clearSession();
  redirect("/");
}

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    // The backend deliberately returns one message for both "no such email" and "wrong
    // password", so passing it through does not leak which accounts exist.
    return error.message;
  }
  // A network failure or a backend that is not running. Do not show the raw error -
  // it can contain internal hostnames.
  return "Could not reach the server. Please try again.";
}
