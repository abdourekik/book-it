"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { bookSlotAction } from "./actions";

/**
 * Pick a time and confirm it.
 *
 * The slots arrive as props, already fetched on the server - this component never
 * fetches. Its only state is "which time did the user tap" and the guest details, which
 * is genuine local UI state rather than a cached copy of server data.
 */

type Props = {
  slug: string;
  serviceId: number;
  serviceName: string;
  timezone: string;
  date: string;
  /** ISO 8601 UTC instants. */
  slots: string[];
  signedInAs: { name: string; email: string } | null;
};

export function SlotBooking({
  slug,
  serviceId,
  serviceName,
  timezone,
  date,
  slots,
  signedInAs,
}: Props) {
  const router = useRouter();

  const [selected, setSelected] = useState<string | null>(null);
  const [guestName, setGuestName] = useState("");
  const [guestEmail, setGuestEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isBooking, startBooking] = useTransition();

  /**
   * Render a UTC instant in the BUSINESS's timezone.
   *
   * Not the visitor's. Someone in London booking a Paris barber must see the time the
   * barber will be expecting them, or they will arrive an hour out.
   */
  function timeLabel(iso: string): string {
    return new Date(iso).toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: timezone,
    });
  }

  function confirm() {
    if (!selected) return;
    setError(null);

    startBooking(async () => {
      const result = await bookSlotAction({
        slug,
        serviceId,
        startsAt: selected,
        guestName: guestName.trim() || undefined,
        guestEmail: guestEmail.trim() || undefined,
      });

      if (result.ok) {
        router.push(`/bookings/${result.token}`);
        return;
      }

      setError(result.error);
      setSelected(null);
      // The slot may have just been taken by someone else. refresh() re-runs the Server
      // Component, so the list reloads from the database rather than leaving a time on
      // screen that is no longer bookable.
      router.refresh();
    });
  }

  if (slots.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No times available on this day. Try another date.
      </p>
    );
  }

  const canBook =
    selected !== null && (signedInAs !== null || (guestName.trim() && guestEmail.trim()));

  return (
    <>
      {/* Capped height with scrolling: slot_interval_minutes can be 1, which turns an
          eight-hour day into 400+ buttons. One scrollable panel beats an endless page. */}
      <div className="grid max-h-64 grid-cols-3 gap-2 overflow-y-auto rounded-xl border border-slate-200 p-2 sm:grid-cols-4 dark:border-slate-800">
        {slots.map((iso) => (
          <button
            key={iso}
            type="button"
            onClick={() => setSelected(iso)}
            aria-pressed={iso === selected}
            className={`rounded-lg border px-2 py-2 text-sm tabular-nums transition ${
              iso === selected
                ? "border-slate-900 bg-slate-900 text-white dark:border-white dark:bg-white dark:text-slate-900"
                : "border-slate-200 hover:border-slate-400 dark:border-slate-800"
            }`}
          >
            {timeLabel(iso)}
          </button>
        ))}
      </div>

      {error && (
        <p
          role="alert"
          className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
        >
          {error}
        </p>
      )}

      {selected && (
        <section className="mt-6 rounded-xl border border-slate-200 p-5 dark:border-slate-800">
          <h2 className="mb-4 text-sm font-medium text-slate-500">4. Confirm</h2>

          <p className="mb-4 text-sm">
            <span className="font-medium">{serviceName}</span> at{" "}
            <span className="font-medium tabular-nums">{timeLabel(selected)}</span> on {date}
          </p>

          {signedInAs ? (
            <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">
              Booking as {signedInAs.name} ({signedInAs.email})
            </p>
          ) : (
            <div className="mb-4 grid gap-3">
              <input
                type="text"
                placeholder="Your name"
                value={guestName}
                onChange={(event) => setGuestName(event.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              />
              <input
                type="email"
                placeholder="Your email"
                value={guestEmail}
                onChange={(event) => setGuestEmail(event.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              />
              <p className="text-xs text-slate-500">
                No account needed — you will get a link to manage this booking.
              </p>
            </div>
          )}

          <button
            type="button"
            onClick={confirm}
            disabled={!canBook || isBooking}
            className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-200"
          >
            {isBooking ? "Booking…" : "Confirm booking"}
          </button>
        </section>
      )}
    </>
  );
}
