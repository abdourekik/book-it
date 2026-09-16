"use client";

import { useState, useTransition } from "react";

import { cancelBookingAction } from "./actions";

/**
 * Cancels a customer's appointment on the owner's behalf.
 *
 * Confirms first. This cancels someone else's plans and sends them an email — far too
 * consequential for a single stray click in a list.
 */
export function CancelBookingButton({ bookingId }: { bookingId: number }) {
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function cancel() {
    setError(null);
    startTransition(async () => {
      const result = await cancelBookingAction(bookingId);
      if (result.error) setError(result.error);
      else setConfirming(false);
    });
  }

  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm transition hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
      >
        Cancel
      </button>
    );
  }

  return (
    <div className="text-right">
      <p className="mb-2 text-xs text-slate-500">Cancel and email the customer?</p>
      {error && (
        <p role="alert" className="mb-2 text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={cancel}
          disabled={isPending}
          className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-60"
        >
          {isPending ? "Cancelling…" : "Yes"}
        </button>
        <button
          type="button"
          onClick={() => setConfirming(false)}
          disabled={isPending}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700"
        >
          No
        </button>
      </div>
    </div>
  );
}
