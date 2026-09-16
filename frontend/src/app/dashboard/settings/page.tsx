import type { Metadata } from "next";

import { AvailabilityEditor } from "./AvailabilityEditor";
import { BusinessForm } from "./BusinessForm";
import { ServicesSection } from "./ServicesSection";
import { TimeOffSection } from "./TimeOffSection";
import { ApiError, api } from "@/lib/api";
import { requireOwner } from "@/lib/require-auth";

export const metadata: Metadata = { title: "Settings" };

export default async function SettingsPage() {
  const { token } = await requireOwner();

  // Before a business exists there is nothing else to configure, so the page shows the
  // creation form alone rather than four empty sections.
  let business;
  try {
    business = await api.owner.business(token);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return (
        <main className="mx-auto max-w-2xl px-6 py-12">
          <h1 className="text-2xl font-semibold tracking-tight">Set up your business</h1>
          <p className="mt-2 text-sm text-slate-500">
            You can change any of this later — except the web address.
          </p>
          <div className="mt-8">
            <BusinessForm business={null} />
          </div>
        </main>
      );
    }
    throw error;
  }

  const [services, availability, timeOff] = await Promise.all([
    api.owner.services(token),
    api.owner.availability(token),
    api.owner.timeOff(token),
  ]);

  return (
    <main className="mx-auto max-w-2xl space-y-12 px-6 py-12">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">{business.name}</p>
      </div>

      <section>
        <h2 className="mb-4 text-lg font-medium">Business</h2>
        <BusinessForm business={business} />
      </section>

      <section>
        <h2 className="mb-4 text-lg font-medium">Services</h2>
        <ServicesSection services={services} />
      </section>

      <section>
        <h2 className="mb-1 text-lg font-medium">Weekly hours</h2>
        <p className="mb-4 text-sm text-slate-500">
          Times are in {business.timezone}. Add two rows to one day for a lunch break.
        </p>
        <AvailabilityEditor rules={availability} />
      </section>

      <section>
        <h2 className="mb-1 text-lg font-medium">Time off</h2>
        <p className="mb-4 text-sm text-slate-500">
          Holidays and closures. These override your weekly hours.
        </p>
        <TimeOffSection timeOff={timeOff} timezone={business.timezone} />
      </section>
    </main>
  );
}
