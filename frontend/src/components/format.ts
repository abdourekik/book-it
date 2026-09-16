/**
 * Date formatting helpers.
 *
 * Which timezone to use is a decision, not a default, so each helper says whose clock
 * it renders in. Getting this wrong is how someone arrives an hour late.
 */

/** In the viewer's own timezone and locale - for their own bookings. */
export function formatForViewer(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** In a specific timezone - for anything about a business's schedule. */
export function formatInZone(iso: string, timezone: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: timezone,
  });
}

export function timeInZone(iso: string, timezone: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

export const WEEKDAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
