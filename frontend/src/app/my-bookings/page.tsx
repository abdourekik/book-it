import type { Metadata } from "next";
import Link from "next/link";

import { formatForViewer } from "@/components/format";
import { api } from "@/lib/api";
import { requireUser } from "@/lib/require-auth";

export const metadata: Metadata = { title: "My bookings" };

const STATUS_STYLE: Record<string, string> = {
  confirmed: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  cancelled: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
  completed: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  no_show: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
};

export default async function MyBookingsPage() {
  const { token } = await requireUser();
  const bookings = await api.myBookings(token);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">My bookings</h1>

      {bookings.length === 0 ? (
        <p className="mt-6 text-slate-600 dark:text-slate-400">
          You have no bookings yet.
        </p>
      ) : (
        <ul className="mt-8 space-y-3">
          {bookings.map((booking) => (
            <li
              key={booking.id}
              className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 px-5 py-4 dark:border-slate-800"
            >
              <div>
                <p className="font-medium">{booking.service.name}</p>
                {/* The viewer's own timezone - this is their calendar. */}
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  {formatForViewer(booking.starts_at)}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                    STATUS_STYLE[booking.status] ?? STATUS_STYLE.completed
                  }`}
                >
                  {booking.status.replace("_", " ")}
                </span>
                <Link
                  href={`/bookings/${booking.access_token}`}
                  className="text-sm font-medium underline"
                >
                  Manage
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-10 text-sm text-slate-500">
        Bookings made without signing in do not appear here — they are managed through
        the link in the confirmation email.
      </p>
    </main>
  );
}
