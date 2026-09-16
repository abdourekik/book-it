"use server";

import { ApiError, api } from "@/lib/api";
import { getSessionToken } from "@/lib/session";

/**
 * Server Action for the public booking page.
 *
 * Only booking needs an action - the slot list is fetched by the Server Component
 * itself, so there is no client-side data fetching at all. Running here keeps
 * API_BASE_URL and the session cookie on the server, and avoids any cross-origin
 * request (and therefore any CORS configuration).
 */

export type BookingResult =
  | { ok: true; token: string }
  | { ok: false; error: string };

export async function bookSlotAction(input: {
  slug: string;
  serviceId: number;
  startsAt: string;
  guestName?: string;
  guestEmail?: string;
}): Promise<BookingResult> {
  const token = await getSessionToken();

  try {
    const booking = await api.createBooking(
      {
        business_slug: input.slug,
        service_id: input.serviceId,
        starts_at: input.startsAt,
        // A signed-in customer must NOT send guest details - the backend rejects both
        // together, mirroring the database's customer_xor_guest constraint.
        ...(token ? {} : { guest_name: input.guestName, guest_email: input.guestEmail }),
      },
      token,
    );
    return { ok: true, token: booking.access_token };
  } catch (error) {
    return { ok: false, error: describe(error) };
  }
}

function describe(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Could not reach the server. Please try again.";
}
