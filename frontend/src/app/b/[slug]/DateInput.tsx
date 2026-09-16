"use client";

import { useRouter } from "next/navigation";

/**
 * A date picker that navigates instead of holding state.
 *
 * Changing the date pushes a new URL; the Server Component re-renders with the new
 * day's times. The selected date lives in exactly one place - the URL - so it cannot
 * drift out of step with what is displayed.
 */
export function DateInput({
  slug,
  serviceId,
  date,
  min,
}: {
  slug: string;
  serviceId: number;
  date: string;
  min: string;
}) {
  const router = useRouter();

  return (
    <input
      type="date"
      value={date}
      min={min}
      aria-label="Appointment date"
      onChange={(event) => {
        // scroll: false keeps the page where it is instead of jumping to the top.
        router.push(`/b/${slug}?service=${serviceId}&date=${event.target.value}`, {
          scroll: false,
        });
      }}
      className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
    />
  );
}
