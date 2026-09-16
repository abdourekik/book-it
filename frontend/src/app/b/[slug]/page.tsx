import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DateInput } from "./DateInput";
import { SlotBooking } from "./SlotBooking";
import { ApiError, api } from "@/lib/api";
import { getCurrentUser } from "@/lib/session";

/**
 * The public page a customer lands on: /b/joes-barbershop?service=1&date=2026-10-06
 *
 * The chosen service and day live in the URL, not in React state. That means this whole
 * page - including the list of free times - is rendered on the server:
 *
 *   - no loading spinner, because the times arrive with the HTML
 *   - no client-side fetch, so API_BASE_URL stays server-side
 *   - the URL is shareable and the back button works
 *   - no useEffect, and therefore none of the stale-response races that come with
 *     fetching on every state change
 *
 * Only the parts that genuinely need interactivity - the date input and the confirm
 * form - are Client Components.
 */

type Props = {
  // Both are Promises in this version of Next.js and must be awaited.
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ service?: string; date?: string }>;
};

/** Today's date as the BUSINESS sees it, not as the visitor's browser sees it. */
function todayIn(timezone: string): string {
  // en-CA formats as YYYY-MM-DD, which is what <input type="date"> and the API expect.
  return new Intl.DateTimeFormat("en-CA", { timeZone: timezone }).format(new Date());
}

async function loadBusiness(slug: string) {
  try {
    return await api.business(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  try {
    const business = await api.business(slug);
    return {
      title: `Book with ${business.name} · Book-it`,
      description: business.description ?? `Book an appointment with ${business.name}.`,
    };
  } catch {
    return { title: "Book-it" };
  }
}

export default async function BusinessPage({ params, searchParams }: Props) {
  const { slug } = await params;
  const query = await searchParams;

  const [business, user] = await Promise.all([loadBusiness(slug), getCurrentUser()]);

  if (business.services.length === 0) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <h1 className="text-3xl font-semibold tracking-tight">{business.name}</h1>
        <p className="mt-6 text-slate-600 dark:text-slate-400">
          This business has not published any services yet.
        </p>
      </main>
    );
  }

  // Fall back rather than 404 on a bad query string: a stale bookmark pointing at a
  // retired service should still show a usable page.
  const service =
    business.services.find((s) => String(s.id) === query.service) ?? business.services[0];
  const today = todayIn(business.timezone);
  const date = query.date && query.date >= today ? query.date : today;

  const result = await api
    .slots(business.slug, service.id, date)
    .then((data) => ({ ok: true as const, data }))
    .catch((error) => ({
      ok: false as const,
      error: error instanceof ApiError ? error.message : "Could not load available times.",
    }));

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <header className="border-b border-slate-200 pb-6 dark:border-slate-800">
        <h1 className="text-3xl font-semibold tracking-tight">{business.name}</h1>
        {business.description && (
          <p className="mt-2 text-slate-600 dark:text-slate-400">{business.description}</p>
        )}
        <p className="mt-3 text-sm text-slate-500">
          All times shown in {business.timezone.replace("_", " ")}
        </p>
      </header>

      <section className="mt-8">
        <h2 className="mb-3 text-sm font-medium text-slate-500">1. Choose a service</h2>
        <div className="grid gap-2">
          {business.services.map((s) => {
            const active = s.id === service.id;
            return (
              // Plain links, so choosing a service works even before JavaScript loads.
              <Link
                key={s.id}
                href={`/b/${business.slug}?service=${s.id}&date=${date}`}
                scroll={false}
                aria-current={active ? "true" : undefined}
                className={`flex items-center justify-between rounded-xl border px-4 py-3 transition ${
                  active
                    ? "border-slate-900 bg-slate-50 dark:border-white dark:bg-slate-900"
                    : "border-slate-200 hover:border-slate-400 dark:border-slate-800"
                }`}
              >
                <span>
                  <span className="block font-medium">{s.name}</span>
                  <span className="text-sm text-slate-500">{s.duration_minutes} minutes</span>
                </span>
                <span className="text-sm font-medium">
                  {s.price} {s.currency}
                </span>
              </Link>
            );
          })}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-sm font-medium text-slate-500">2. Choose a day</h2>
        <DateInput slug={business.slug} serviceId={service.id} date={date} min={today} />
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-sm font-medium text-slate-500">
          3. Choose a time
          {result.ok && result.data.slots.length > 0 && (
            <span className="ml-2 font-normal">({result.data.slots.length} available)</span>
          )}
        </h2>

        {!result.ok ? (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            {result.error}
          </p>
        ) : (
          <SlotBooking
            slug={business.slug}
            serviceId={service.id}
            serviceName={service.name}
            timezone={business.timezone}
            date={date}
            slots={result.data.slots}
            signedInAs={user ? { name: user.full_name, email: user.email } : null}
          />
        )}
      </section>
    </main>
  );
}
