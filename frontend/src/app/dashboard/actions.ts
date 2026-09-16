"use server";

import { revalidatePath } from "next/cache";

import { ApiError, api } from "@/lib/api";
import { getSessionToken } from "@/lib/session";

/**
 * Owner mutations.
 *
 * Each one reads the session token from the httpOnly cookie on the server, so the
 * browser never holds it and no script on the page can replay these calls.
 *
 * Errors are returned rather than thrown. A Server Action that throws shows the user a
 * generic error screen and loses whatever they typed; returning the message lets the
 * form render it beside the field and keep the rest of the input.
 */

export type Result = { error: string | null };

async function run(fn: (token: string) => Promise<unknown>): Promise<Result> {
  const token = await getSessionToken();
  if (!token) return { error: "Your session expired. Please sign in again." };

  try {
    await fn(token);
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message };
    return { error: "Could not reach the server. Please try again." };
  }

  // Both pages read owner data, so both are stale after any change.
  revalidatePath("/dashboard");
  revalidatePath("/dashboard/settings");
  return { error: null };
}

function text(formData: FormData, field: string): string {
  return String(formData.get(field) ?? "").trim();
}

/**
 * <input type="datetime-local"> yields "2026-12-24T09:00" with no offset. The backend
 * rejects naive timestamps on purpose, so interpret it in the browser's timezone and
 * send a proper instant.
 */
function toInstant(value: string): string {
  return value ? new Date(value).toISOString() : "";
}

/* ------------------------------------------------------------- business */

export async function createBusinessAction(_prev: Result, formData: FormData): Promise<Result> {
  return run((token) =>
    api.owner.createBusiness(token, {
      name: text(formData, "name"),
      slug: text(formData, "slug"),
      timezone: text(formData, "timezone"),
      description: text(formData, "description") || null,
      slot_interval_minutes: Number(formData.get("slot_interval_minutes") ?? 1),
    }),
  );
}

export async function updateBusinessAction(_prev: Result, formData: FormData): Promise<Result> {
  return run((token) =>
    api.owner.updateBusiness(token, {
      name: text(formData, "name"),
      timezone: text(formData, "timezone"),
      description: text(formData, "description") || null,
      slot_interval_minutes: Number(formData.get("slot_interval_minutes") ?? 1),
    }),
  );
}

/* ------------------------------------------------------------- services */

export async function createServiceAction(_prev: Result, formData: FormData): Promise<Result> {
  return run((token) =>
    api.owner.createService(token, {
      name: text(formData, "name"),
      duration_minutes: Number(formData.get("duration_minutes") ?? 0),
      price: text(formData, "price") || "0",
      currency: (text(formData, "currency") || "EUR").toUpperCase(),
    }),
  );
}

export async function retireServiceAction(id: number): Promise<Result> {
  return run((token) => api.owner.retireService(token, id));
}

export async function reactivateServiceAction(id: number): Promise<Result> {
  return run((token) => api.owner.updateService(token, id, { is_active: true }));
}

/* --------------------------------------------------------- availability */

export async function replaceAvailabilityAction(
  rules: { weekday: number; start_time: string; end_time: string }[],
): Promise<Result> {
  return run((token) => api.owner.replaceAvailability(token, rules));
}

/* ------------------------------------------------------------- time off */

export async function createTimeOffAction(_prev: Result, formData: FormData): Promise<Result> {
  return run((token) =>
    api.owner.createTimeOff(token, {
      starts_at: toInstant(text(formData, "starts_at")),
      ends_at: toInstant(text(formData, "ends_at")),
      reason: text(formData, "reason") || null,
    }),
  );
}

export async function deleteTimeOffAction(id: number): Promise<Result> {
  return run((token) => api.owner.deleteTimeOff(token, id));
}

/* ------------------------------------------------------------- bookings */

export async function cancelBookingAction(bookingId: number): Promise<Result> {
  return run((token) => api.owner.cancelBooking(token, bookingId));
}
