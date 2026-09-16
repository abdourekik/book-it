import Link from "next/link";

import { logoutAction } from "@/app/(auth)/actions";
import { getCurrentUser } from "@/lib/session";

/** Site header. A Server Component, so it knows who is signed in without any fetch. */
export async function Nav() {
  const user = await getCurrentUser();

  return (
    <header className="border-b border-slate-200 dark:border-slate-800">
      <nav className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
        <Link href="/" className="font-semibold tracking-tight">
          Book-it
        </Link>

        <div className="flex items-center gap-4 text-sm">
          {user ? (
            <>
              {user.role === "owner" ? (
                <Link href="/dashboard" className="hover:underline">
                  Dashboard
                </Link>
              ) : (
                <Link href="/my-bookings" className="hover:underline">
                  My bookings
                </Link>
              )}
              <form action={logoutAction}>
                <button type="submit" className="text-slate-500 hover:underline">
                  Sign out
                </button>
              </form>
            </>
          ) : (
            <>
              <Link href="/login" className="hover:underline">
                Sign in
              </Link>
              <Link
                href="/signup"
                className="rounded-lg bg-slate-900 px-3 py-1.5 font-medium text-white dark:bg-white dark:text-slate-900"
              >
                Sign up
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
