"use client";

import { useActionState, useTransition } from "react";
import { useFormStatus } from "react-dom";

import {
  createServiceAction,
  reactivateServiceAction,
  retireServiceAction,
  type Result,
} from "../actions";
import type { OwnerService } from "@/lib/api";

const EMPTY: Result = { error: null };

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900";

function AddButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-white dark:text-slate-900"
    >
      {pending ? "Adding…" : "Add service"}
    </button>
  );
}

function ServiceRow({ service }: { service: OwnerService }) {
  const [isPending, startTransition] = useTransition();

  function toggle() {
    startTransition(async () => {
      if (service.is_active) await retireServiceAction(service.id);
      else await reactivateServiceAction(service.id);
    });
  }

  return (
    <li
      className={`flex items-center justify-between gap-4 rounded-xl border px-4 py-3 ${
        service.is_active
          ? "border-slate-200 dark:border-slate-800"
          : "border-dashed border-slate-300 text-slate-400 dark:border-slate-700"
      }`}
    >
      <div>
        <p className="font-medium">
          {service.name}
          {!service.is_active && (
            <span className="ml-2 text-xs font-normal">(hidden from customers)</span>
          )}
        </p>
        <p className="text-sm text-slate-500">
          {service.duration_minutes} min · {service.price} {service.currency}
        </p>
      </div>

      <button
        type="button"
        onClick={toggle}
        disabled={isPending}
        className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-60 dark:border-slate-700"
      >
        {isPending ? "…" : service.is_active ? "Retire" : "Restore"}
      </button>
    </li>
  );
}

export function ServicesSection({ services }: { services: OwnerService[] }) {
  const [state, formAction] = useActionState(createServiceAction, EMPTY);

  return (
    <div className="space-y-5">
      {services.length > 0 && (
        <ul className="space-y-2">
          {services.map((service) => (
            <ServiceRow key={service.id} service={service} />
          ))}
        </ul>
      )}

      {/* "Retire" rather than "Delete", because that is what actually happens: existing
          bookings keep pointing at the service, so it is hidden rather than removed. */}
      <p className="text-xs text-slate-500">
        Retiring a service hides it from customers. Existing bookings are unaffected.
      </p>

      <form action={formAction} className="grid gap-3 sm:grid-cols-4">
        <input name="name" placeholder="Service name" required className={`${inputClass} sm:col-span-2`} />
        <input
          name="duration_minutes"
          type="number"
          min={1}
          max={1440}
          placeholder="Minutes"
          required
          className={inputClass}
        />
        <input
          name="price"
          type="number"
          min={0}
          step="0.01"
          placeholder="Price"
          required
          className={inputClass}
        />

        {state.error && (
          <p
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 sm:col-span-4 dark:bg-red-950 dark:text-red-300"
          >
            {state.error}
          </p>
        )}

        <div className="sm:col-span-4">
          <AddButton />
        </div>
      </form>
    </div>
  );
}
