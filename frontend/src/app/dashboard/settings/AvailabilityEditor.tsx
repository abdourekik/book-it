"use client";

import { useState, useTransition } from "react";

import { replaceAvailabilityAction } from "../actions";
import { WEEKDAYS } from "@/components/format";
import type { AvailabilityRule } from "@/lib/api";

/**
 * The whole week, edited together and saved in one request.
 *
 * The API replaces the entire schedule rather than patching individual rules, so this
 * holds the full set in local state and sends it all on save. That matches how an owner
 * thinks about their hours, and means a half-applied schedule cannot exist.
 */

type Row = { weekday: number; start_time: string; end_time: string };

function toRow(rule: AvailabilityRule): Row {
  return {
    weekday: rule.weekday,
    // The API returns "09:00:00"; <input type="time"> wants "09:00".
    start_time: rule.start_time.slice(0, 5),
    end_time: rule.end_time.slice(0, 5),
  };
}

export function AvailabilityEditor({ rules }: { rules: AvailabilityRule[] }) {
  const [rows, setRows] = useState<Row[]>(rules.map(toRow));
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [isPending, startTransition] = useTransition();

  function update(index: number, patch: Partial<Row>) {
    setSaved(false);
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function addRow(weekday: number) {
    setSaved(false);
    setRows((current) => [...current, { weekday, start_time: "09:00", end_time: "17:00" }]);
  }

  function removeRow(index: number) {
    setSaved(false);
    setRows((current) => current.filter((_, i) => i !== index));
  }

  function save() {
    setError(null);
    startTransition(async () => {
      const result = await replaceAvailabilityAction(
        // Seconds appended because the API expects a full time value.
        rows.map((row) => ({
          weekday: row.weekday,
          start_time: `${row.start_time}:00`,
          end_time: `${row.end_time}:00`,
        })),
      );
      if (result.error) setError(result.error);
      else setSaved(true);
    });
  }

  return (
    <div className="space-y-4">
      {WEEKDAYS.map((name, weekday) => {
        const dayRows = rows
          .map((row, index) => ({ row, index }))
          .filter(({ row }) => row.weekday === weekday);

        return (
          <div
            key={name}
            className="flex flex-wrap items-start gap-3 border-b border-slate-100 pb-3 dark:border-slate-800"
          >
            <span className="w-24 pt-2 text-sm font-medium">{name}</span>

            <div className="flex-1 space-y-2">
              {dayRows.length === 0 && (
                <p className="pt-2 text-sm text-slate-400">Closed</p>
              )}

              {dayRows.map(({ row, index }) => (
                <div key={index} className="flex items-center gap-2">
                  <input
                    type="time"
                    value={row.start_time}
                    aria-label={`${name} opening time`}
                    onChange={(e) => update(index, { start_time: e.target.value })}
                    className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
                  />
                  <span className="text-slate-400">to</span>
                  <input
                    type="time"
                    value={row.end_time}
                    aria-label={`${name} closing time`}
                    onChange={(e) => update(index, { end_time: e.target.value })}
                    className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
                  />
                  <button
                    type="button"
                    onClick={() => removeRow(index)}
                    aria-label={`Remove ${name} hours`}
                    className="px-2 text-sm text-slate-400 hover:text-red-600"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={() => addRow(weekday)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700"
            >
              Add hours
            </button>
          </div>
        );
      })}

      {error && (
        <p
          role="alert"
          className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
        >
          {error}
        </p>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={save}
          disabled={isPending}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-white dark:text-slate-900"
        >
          {isPending ? "Saving…" : "Save hours"}
        </button>
        {saved && <span className="text-sm text-emerald-600">Saved</span>}
      </div>
    </div>
  );
}
