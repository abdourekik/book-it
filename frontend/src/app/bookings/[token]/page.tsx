import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CancelButton } from "./CancelButton";
import { ApiError, api } from "@/lib/api";

/**
 * The page a customer reaches from their confirmation link.
 *
 * The token in the URL IS the authorisation - a capability URL. Anyone holding this
 * link may view and cancel this one booking and nothing else, which is how a guest with
 * no account manages their appointment.
 */

type Props = { params: Promise<{ token: string }> };

// Never cached or indexed: the URL is a secret, and a cached copy on a shared machine
// would hand the next person the same power.
export const metadata: Metadata = {
  title: "Your booking",
  robots: { index: false, follow: false },
};

export default async function BookingPage({ params }: Props) {
  const { token } = await params;

  let booking;
  try {
    booking = await api.getBooking(token);
  } catch (error) {
    // 404 for a wrong token, never 403 - confirming that a token exists but is not
    // yours would help someone guess them.
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const starts = new Date(booking.starts_at);
  const cancelled = booking.status === "cancelled";

  return (
    <main className="mx-auto max-w-lg px-6 py-16">
      <p className="text-sm font-medium text-slate-500">
        {cancelled ? "Cancelled" : "Confirmed"}
      </p>
      <h1 className="mt-1 text-3xl font-semibold tracking-tight">
        {cancelled ? "This booking was cancelled" : "You are booked in"}
      </h1>

      <dl
        className={`mt-8 space-y-4 rounded-xl border p-6 ${
          cancelled
            ? "border-slate-200 text-slate-400 dark:border-slate-800"
            : "border-slate-200 dark:border-slate-800"
        }`}
      >
        <div>
          <dt className="text-sm text-slate-500">Service</dt>
          <dd className="font-medium">
            {booking.service.name} · {booking.service.duration_minutes} minutes
          </dd>
        </div>
        <div>
          <dt className="text-sm text-slate-500">When</dt>
          {/* dateStyle/timeStyle render in the VISITOR's timezone, which is what they
              want on their own confirmation - unlike the slot picker, which must show
              the shop's local time. */}
          <dd className="font-medium">
            {starts.toLocaleString(undefined, {
              dateStyle: "full",
              timeStyle: "short",
            })}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-slate-500">Name</dt>
          <dd className="font-medium">{booking.customer_name}</dd>
        </div>
      </dl>

      {!cancelled && (
        <div className="mt-6">
          <CancelButton token={token} />
        </div>
      )}

      <p className="mt-8 text-sm text-slate-500">
        Keep this link — it is the only way to manage this booking without an account.
      </p>

      <Link
        href="/"
        className="mt-6 inline-block text-sm font-medium underline"
      >
        Back to Book-it
      </Link>
    </main>
  );
}
