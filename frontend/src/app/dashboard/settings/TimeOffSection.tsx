"use client";

import { useActionState, useTransition } from "react";
import { useFormStatus } from "react-dom";

import { createTimeOffAction, deleteTimeOffAction, type Result } from "../actions";
import { formatInZone } from "@/components/format";
import type { TimeOff } from "@/lib/api";

const EMPTY: Result = { error: null };

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900";

function AddButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-white dark:text-slate-900"
    >
      {pending ? "Adding…" : "Block out this time"}
    </button>
  );
}

function TimeOffRow({ entry, timezone }: { entry: TimeOff; timezone: string }) {
  const [isPending, startTransition] = useTransition();

  return (
    <li className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 px-4 py-3 dark:border-slate-800">
      <div>
        <p className="text-sm font-medium tabular-nums">
          {formatInZone(entry.starts_at, timezone)} → {formatInZone(entry.ends_at, timezone)}
        </p>
        {entry.reason && <p className="text-sm text-slate-500">{entry.reason}</p>}
      </div>

      <button
        type="button"
        onClick={() => startTransition(async () => void (await deleteTimeOffAction(entry.id)))}
        disabled={isPending}
        className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-60 dark:border-slate-700"
      >
        {isPending ? "…" : "Remove"}
      </button>
    </li>
  );
}

export function TimeOffSection({
  timeOff,
  timezone,
}: {
  timeOff: TimeOff[];
  timezone: string;
}) {
  const [state, formAction] = useActionState(createTimeOffAction, EMPTY);

  return (
    <div className="space-y-5">
      {timeOff.length > 0 && (
        <ul className="space-y-2">
          {timeOff.map((entry) => (
            <TimeOffRow key={entry.id} entry={entry} timezone={timezone} />
          ))}
        </ul>
      )}

      <form action={formAction} className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="starts_at" className="mb-1.5 block text-sm font-medium">
            From
          </label>
          <input id="starts_at" name="starts_at" type="datetime-local" required className={inputClass} />
        </div>
        <div>
          <label htmlFor="ends_at" className="mb-1.5 block text-sm font-medium">
            Until
          </label>
          <input id="ends_at" name="ends_at" type="datetime-local" required className={inputClass} />
        </div>

        <div className="sm:col-span-2">
          <label htmlFor="reason" className="mb-1.5 block text-sm font-medium">
            Reason (optional)
          </label>
          <input id="reason" name="reason" placeholder="Holiday" className={inputClass} />
        </div>

        {state.error && (
          // The most likely error here is the 409 for clashing with a confirmed booking,
          // which tells the owner exactly what to do about it.
          <p
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 sm:col-span-2 dark:bg-red-950 dark:text-red-300"
          >
            {state.error}
          </p>
        )}

        <div className="sm:col-span-2">
          <AddButton />
        </div>
      </form>
    </div>
  );
}
