import type { Metadata } from "next";

import { loginAction } from "../actions";
import { AuthForm, AuthLink, Field } from "../AuthForm";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <AuthForm
      title="Sign in"
      submitLabel="Sign in"
      action={loginAction}
      footer={<>New here? <AuthLink href="/signup">Create an account</AuthLink></>}
    >
      <Field label="Email" name="email" type="email" autoComplete="email" />
      {/* autoComplete="current-password" tells password managers this is a sign-in box,
          not a new password to generate. */}
      <Field
        label="Password"
        name="password"
        type="password"
        autoComplete="current-password"
      />
    </AuthForm>
  );
}
