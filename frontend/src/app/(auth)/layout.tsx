/**
 * Layout for the auth pages.
 *
 * The (auth) folder name is in brackets, which makes it a ROUTE GROUP: it organises
 * files and shares this layout, but contributes nothing to the URL. The page at
 * src/app/(auth)/login/page.tsx is served at /login, not /auth/login.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      {children}
    </main>
  );
}
