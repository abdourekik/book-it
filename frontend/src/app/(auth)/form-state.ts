/**
 * Shared types and constants for the auth forms.
 *
 * Separate from actions.ts on purpose. A file marked "use server" may export ONLY async
 * functions - everything exported from it becomes a callable server endpoint, so a
 * plain object is rejected at build time. Constants and types live here instead.
 */

export type FormState = { error: string | null };

/** What useActionState holds before the first submission. */
export const EMPTY_FORM_STATE: FormState = { error: null };
