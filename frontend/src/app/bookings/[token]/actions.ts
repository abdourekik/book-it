"use server";

import { revalidatePath } from "next/cache";

import { ApiError, api } from "@/lib/api";

export async function cancelBookingAction(token: string): Promise<{ error: string | null }> {
  try {
    await api.cancelBooking(token);
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message };
    return { error: "Could not reach the server. Please try again." };
  }

  // Tell Next.js this page's data is stale so the Server Component re-runs and the
  // status flips to "Cancelled". Without this the user would cancel and see no change.
  revalidatePath(`/bookings/${token}`);
  return { error: null };
}
