"use client";

import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { createBusinessAction, updateBusinessAction, type Result } from "../actions";
import type { Business } from "@/lib/api";

const EMPTY: Result = { error: null };

// A short list rather than all ~600 IANA zones. The API validates whatever arrives, so
// this is convenience, not the enforcement.
const COMMON_TIMEZONES = [
  "Europe/Paris",
  "Europe/London",
  "Europe/Madrid",
  "Europe/Berlin",
  "Africa/Tunis",
  "Africa/Casablanca",
  "America/New_York",
  "America/Los_Angeles",
  "UTC",
];

function Save({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-white dark:text-slate-900"
    >
      {pending ? "Saving…" : label}
    </button>
  );
}

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900";

export function BusinessForm({ business }: { business: Business | null }) {
  const isNew = business === null;
  const [state, formAction] = useActionState(
    isNew ? createBusinessAction : updateBusinessAction,
    EMPTY,
  );

  return (
    <form action={formAction} className="space-y-4">
      <div>
        <label htmlFor="name" className="mb-1.5 block text-sm font-medium">
          Name
        </label>
        <input
          id="name"
          name="name"
          required
          defaultValue={business?.name ?? ""}
          className={inputClass}
        />
      </div>

      {isNew && (
        <div>
          <label htmlFor="slug" className="mb-1.5 block text-sm font-medium">
            Web address
          </label>
          <input
            id="slug"
            name="slug"
            required
            placeholder="joes-barbershop"
            pattern="[a-z0-9]+(-[a-z0-9]+)*"
            className={inputClass}
          />
          {/* Only offered at creation. Changing it later would break every link a
              customer has already been given, including the ones in their emails. */}
          <p className="mt-1.5 text-xs text-slate-500">
            Your page will be /b/your-address. Lowercase letters, numbers and hyphens.
            This cannot be changed later.
          </p>
        </div>
      )}

      <div>
        <label htmlFor="timezone" className="mb-1.5 block text-sm font-medium">
          Timezone
        </label>
        <input
          id="timezone"
          name="timezone"
          required
          list="timezones"
          defaultValue={business?.timezone ?? "Europe/Paris"}
          className={inputClass}
        />
        <datalist id="timezones">
          {COMMON_TIMEZONES.map((zone) => (
            <option key={zone} value={zone} />
          ))}
        </datalist>
        <p className="mt-1.5 text-xs text-slate-500">
          Your opening hours are interpreted in this zone, and daylight saving is handled
          for you.
        </p>
      </div>

      <div>
        <label htmlFor="description" className="mb-1.5 block text-sm font-medium">
          Description
        </label>
        <textarea
          id="description"
          name="description"
          rows={2}
          defaultValue={business?.description ?? ""}
          className={inputClass}
        />
      </div>

      <div>
        <label htmlFor="slot_interval_minutes" className="mb-1.5 block text-sm font-medium">
          Appointment times every
        </label>
        <select
          id="slot_interval_minutes"
          name="slot_interval_minutes"
          defaultValue={String(business?.slot_interval_minutes ?? 15)}
          className={inputClass}
        >
          <option value="1">minute (every free minute)</option>
          <option value="5">5 minutes</option>
          <option value="10">10 minutes</option>
          <option value="15">15 minutes</option>
          <option value="30">30 minutes</option>
          <option value="60">hour</option>
        </select>
        <p className="mt-1.5 text-xs text-slate-500">
          Smaller values pack the day tighter but give customers a much longer list to
          scroll.
        </p>
      </div>

      {state.error && (
        <p
          role="alert"
          className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
        >
          {state.error}
        </p>
      )}

      <Save label={isNew ? "Create business" : "Save changes"} />
    </form>
  );
}
