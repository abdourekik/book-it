import type { Metadata } from "next";

import { signupAction } from "../actions";
import { AuthForm, AuthLink, Field } from "../AuthForm";

export const metadata: Metadata = { title: "Create an account · Book-it" };

export default function SignupPage() {
  return (
    <AuthForm
      title="Create an account"
      submitLabel="Create account"
      action={signupAction}
      footer={<>Already have an account? <AuthLink href="/login">Sign in</AuthLink></>}
    >
      <Field label="Full name" name="full_name" autoComplete="name" />
      <Field label="Email" name="email" type="email" autoComplete="email" />
      <Field
        label="Password"
        name="password"
        type="password"
        autoComplete="new-password"
        hint="At least 8 characters. A long phrase beats a short jumble."
      />

      <div>
        <label htmlFor="role" className="mb-1.5 block text-sm font-medium">
          I want to
        </label>
        <select
          id="role"
          name="role"
          defaultValue="customer"
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10 dark:border-slate-700 dark:bg-slate-900 dark:focus:border-slate-300"
        >
          <option value="customer">Book appointments</option>
          <option value="owner">Take bookings for my business</option>
        </select>
      </div>
    </AuthForm>
  );
}
