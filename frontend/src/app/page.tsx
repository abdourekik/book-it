import Link from "next/link";

import { logoutAction } from "./(auth)/actions";
import { getCurrentUser } from "@/lib/session";

/**
 * The home page.
 *
 * A Server Component - note there is no "use client" and no useEffect. It runs on the
 * server, awaits the current user directly, and sends finished HTML. The browser never
 * makes an API call for this, and the token never leaves the server.
 */
export default async function Home() {
  const user = await getCurrentUser();

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <h1 className="text-4xl font-semibold tracking-tight">Book-it</h1>
      <p className="mt-3 text-lg text-slate-600 dark:text-slate-400">
        Appointment booking for barbers, clinics, and tutors.
      </p>

      {user ? (
        <div className="mt-10 rounded-xl border border-slate-200 p-6 dark:border-slate-800">
          <p className="text-sm text-slate-500">Signed in as</p>
          <p className="mt-1 text-lg font-medium">{user.full_name}</p>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {user.email} · {user.role}
          </p>

          <form action={logoutAction} className="mt-5">
            <button
              type="submit"
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium transition hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              Sign out
            </button>
          </form>
        </div>
      ) : (
        <div className="mt-10 flex gap-3">
          <Link
            href="/login"
            className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-200"
          >
            Sign in
          </Link>
          <Link
            href="/signup"
            className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-medium transition hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Create an account
          </Link>
        </div>
      )}

      <p className="mt-12 text-sm text-slate-500">
        Booking pages come next. The API is already complete — see{" "}
        <a
          href="http://localhost:8000/docs"
          className="underline"
          target="_blank"
          rel="noreferrer"
        >
          the interactive docs
        </a>
        .
      </p>
    </main>
  );
}
