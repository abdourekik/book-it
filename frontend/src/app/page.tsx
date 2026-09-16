import Link from "next/link";

import { getCurrentUser } from "@/lib/session";

/**
 * The landing page.
 *
 * A Server Component: it awaits the current user directly and ships finished HTML, so
 * there is no spinner and no client-side fetch. What it shows depends on who is
 * reading it - a visitor needs a reason to sign up, an owner needs their dashboard, and
 * a customer needs their bookings.
 */

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-4">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-sm font-medium text-white dark:bg-white dark:text-slate-900">
        {n}
      </span>
      <div>
        <p className="font-medium">{title}</p>
        <p className="text-sm text-slate-600 dark:text-slate-400">{children}</p>
      </div>
    </li>
  );
}

export default async function Home() {
  const user = await getCurrentUser();

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-4xl font-semibold tracking-tight">Book-it</h1>
      <p className="mt-3 text-lg text-slate-600 dark:text-slate-400">
        Appointment booking for barbers, clinics, and tutors. Publish your hours, share
        one link, and let customers book themselves in.
      </p>

      {/* ---------------------------------------------------------- owner */}
      {user?.role === "owner" && (
        <div className="mt-10 rounded-xl border border-slate-200 p-6 dark:border-slate-800">
          <p className="text-sm text-slate-500">Signed in as {user.full_name}</p>
          <p className="mt-3">Manage your services, hours, and bookings.</p>
          <Link
            href="/dashboard"
            className="mt-5 inline-block rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white dark:bg-white dark:text-slate-900"
          >
            Go to dashboard
          </Link>
        </div>
      )}

      {/* ------------------------------------------------------- customer */}
      {user?.role === "customer" && (
        <div className="mt-10 rounded-xl border border-slate-200 p-6 dark:border-slate-800">
          <p className="text-sm text-slate-500">Signed in as {user.full_name}</p>
          <p className="mt-3">
            To book an appointment, open the link a business shared with you — it looks
            like <code className="rounded bg-slate-100 px-1.5 py-0.5 text-sm dark:bg-slate-800">/b/their-name</code>.
          </p>
          <Link href="/my-bookings" className="mt-5 inline-block text-sm font-medium underline">
            See my bookings
          </Link>
        </div>
      )}

      {/* -------------------------------------------------------- visitor */}
      {!user && (
        <div className="mt-10 flex flex-wrap gap-3">
          <Link
            href="/signup"
            className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white dark:bg-white dark:text-slate-900"
          >
            Get started
          </Link>
          <Link
            href="/login"
            className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-medium dark:border-slate-700"
          >
            Sign in
          </Link>
        </div>
      )}

      <section className="mt-16">
        <h2 className="text-sm font-medium text-slate-500">For businesses</h2>
        <ol className="mt-5 space-y-5">
          <Step n={1} title="Create an account">
            Choose &ldquo;Take bookings for my business&rdquo; when you sign up.
          </Step>
          <Step n={2} title="Add your services and hours">
            Name, duration, and price for each service. Set your weekly opening hours and
            block out any time off.
          </Step>
          <Step n={3} title="Share your link">
            Customers pick a service, a day, and a free time. No account needed on their
            side — they get a link to manage the booking.
          </Step>
        </ol>
      </section>

      <section className="mt-14 border-t border-slate-200 pt-8 dark:border-slate-800">
        <h2 className="text-sm font-medium text-slate-500">Built with</h2>
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
          FastAPI and PostgreSQL on the backend, Next.js on the front. Times are stored in
          UTC and shown in each business&rsquo;s timezone, so daylight saving never moves
          an appointment. Double-booking is prevented by a database constraint rather than
          application code — there is a test that fires ten simultaneous requests at one
          slot and asserts exactly one wins.
        </p>
        <p className="mt-4 text-sm">
          <a
            href="https://github.com/abdourekik/book-it"
            className="font-medium underline"
            target="_blank"
            rel="noreferrer"
          >
            Source on GitHub
          </a>
        </p>
      </section>
    </main>
  );
}
