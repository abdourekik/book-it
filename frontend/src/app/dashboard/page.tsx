import type { Metadata } from "next";
import Link from "next/link";

import { CancelBookingButton } from "./CancelBookingButton";
import { formatInZone } from "@/components/format";
import { ApiError, api } from "@/lib/api";
import { requireOwner } from "@/lib/require-auth";

export const metadata: Metadata = { title: "Dashboard" };

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 p-5 dark:border-slate-800">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export default async function DashboardPage() {
  const { token } = await requireOwner();

  // An owner can sign up before creating a business, so this 404 is an expected state
  // rather than an error - send them to set one up.
  let business;
  try {
    business = await api.owner.business(token);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return (
        <main className="mx-auto max-w-3xl px-6 py-12">
          <h1 className="text-2xl font-semibold tracking-tight">Welcome</h1>
          <p className="mt-3 text-slate-600 dark:text-slate-400">
            Set up your business to start taking bookings.
          </p>
          <Link
            href="/dashboard/settings"
            className="mt-6 inline-block rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white dark:bg-white dark:text-slate-900"
          >
            Set up my business
          </Link>
        </main>
      );
    }
    throw error;
  }

  // Two independent requests, so they go out together rather than one after the other.
  const [stats, bookings] = await Promise.all([
    api.owner.stats(token),
    api.owner.bookings(token, 7),
  ]);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{business.name}</h1>
          <p className="mt-1 text-sm text-slate-500">
            Your booking page:{" "}
            <Link href={`/b/${business.slug}`} className="underline">
              /b/{business.slug}
            </Link>
          </p>
        </div>
        <Link
          href="/dashboard/settings"
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium dark:border-slate-700"
        >
          Settings
        </Link>
      </div>

      <section className="mt-8 grid gap-3 sm:grid-cols-3">
        <Stat
          label="This week"
          value={String(stats.bookings_this_week)}
          hint="Mon–Sun, your local week"
        />
        <Stat
          label="Cancellation rate"
          value={`${Math.round(stats.cancellation_rate * 100)}%`}
          hint={`${stats.total_bookings} bookings all time`}
        />
        <Stat label="Busiest day" value={stats.busiest_weekday ?? "—"} />
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-medium text-slate-500">Next 7 days</h2>

        {bookings.length === 0 ? (
          <p className="mt-4 text-slate-600 dark:text-slate-400">
            Nothing booked in the next week.
          </p>
        ) : (
          <ul className="mt-4 space-y-2">
            {bookings.map((booking) => (
              <li
                key={booking.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 px-5 py-4 dark:border-slate-800"
              >
                <div>
                  {/* The BUSINESS's timezone, not the viewer's: this is the owner's own
                      schedule, and they may well be reading it while travelling. */}
                  <p className="font-medium tabular-nums">
                    {formatInZone(booking.starts_at, business.timezone)}
                  </p>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {booking.service_name} · {booking.customer_name} ({booking.customer_email})
                  </p>
                </div>
                <CancelBookingButton bookingId={booking.id} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
