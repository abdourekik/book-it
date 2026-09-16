"use client";

import Link from "next/link";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { EMPTY_FORM_STATE, type FormState } from "./form-state";

/**
 * The shared shell for the sign-in and sign-up forms.
 *
 * "use client" because it needs interactivity - useActionState tracks what the server
 * sent back, and useFormStatus disables the button while the request is in flight.
 * The action itself still runs on the server.
 */

type Props = {
  title: string;
  submitLabel: string;
  action: (previous: FormState, formData: FormData) => Promise<FormState>;
  children: React.ReactNode;
  footer: React.ReactNode;
};

function SubmitButton({ label }: { label: string }) {
  // Must be a separate component: useFormStatus reads the status of the nearest parent
  // <form>, so it cannot be called in the component that renders that form.
  const { pending } = useFormStatus();

  return (
    <button
      type="submit"
      disabled={pending}
      className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-200"
    >
      {pending ? "Please wait…" : label}
    </button>
  );
}

export function AuthForm({ title, submitLabel, action, children, footer }: Props) {
  const [state, formAction] = useActionState(action, EMPTY_FORM_STATE);

  return (
    <div className="mx-auto w-full max-w-sm">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">{title}</h1>

      <form action={formAction} className="space-y-4">
        {children}

        {state.error && (
          // role="alert" makes screen readers announce the failure instead of leaving
          // someone wondering why nothing happened.
          <p
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
          >
            {state.error}
          </p>
        )}

        <SubmitButton label={submitLabel} />
      </form>

      <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">{footer}</p>
    </div>
  );
}

export function Field({
  label,
  name,
  type = "text",
  autoComplete,
  required = true,
  hint,
}: {
  label: string;
  name: string;
  type?: string;
  autoComplete?: string;
  required?: boolean;
  hint?: string;
}) {
  return (
    <div>
      {/* htmlFor/id pairing lets a click on the label focus the input, and tells screen
          readers which text describes which box. */}
      <label htmlFor={name} className="mb-1.5 block text-sm font-medium">
        {label}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        required={required}
        autoComplete={autoComplete}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10 dark:border-slate-700 dark:bg-slate-900 dark:focus:border-slate-300"
      />
      {hint && <p className="mt-1.5 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export function AuthLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="font-medium text-slate-900 underline dark:text-white">
      {children}
    </Link>
  );
}
