"use client";

import { useState, useTransition } from "react";

import { cancelBookingAction } from "./actions";

/**
 * Cancelling is destructive and cannot be undone, so it asks first. A single-click
 * "Cancel" next to booking details is far too easy to hit by accident.
 */
export function CancelButton({ token }: { token: string }) {
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function cancel() {
    setError(null);
    startTransition(async () => {
      const result = await cancelBookingAction(token);
      if (result.error) setError(result.error);
    });
  }

  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium transition hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
      >
        Cancel this booking
      </button>
    );
  }

  return (
    <div className="rounded-xl border border-red-200 p-4 dark:border-red-900">
      <p className="text-sm">Cancel this appointment? This cannot be undone.</p>

      {error && (
        <p role="alert" className="mt-2 text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={cancel}
          disabled={isPending}
          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-60"
        >
          {isPending ? "Cancelling…" : "Yes, cancel it"}
        </button>
        <button
          type="button"
          onClick={() => setConfirming(false)}
          disabled={isPending}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium transition hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
        >
          Keep it
        </button>
      </div>
    </div>
  );
}
