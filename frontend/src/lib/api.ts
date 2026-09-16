/**
 * Typed client for the Book-it API.
 *
 * Every call goes through `request`, so error handling, JSON parsing, and the bearer
 * token are written once rather than in every component.
 *
 * These types are hand-written to match the backend's Pydantic schemas. Once the API
 * settles, `openapi-typescript` can generate them from /openapi.json instead, which
 * makes a backend change that breaks the frontend a compile error rather than a
 * runtime surprise.
 */

const BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

/** An error the API returned deliberately, with the status it used. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  token?: string;
  /** Next.js caching. Anything user-specific or time-sensitive must not be cached. */
  cache?: RequestCache;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, token, cache = "no-store" } = options;

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    cache,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }

  // 204 No Content has an empty body; calling .json() on it throws.
  if (response.status === 204) return undefined as T;

  return (await response.json()) as T;
}

/**
 * Turn FastAPI's error shapes into one readable sentence.
 *
 * FastAPI uses `detail`, but it is a string for HTTPException and an array of field
 * errors for a 422 validation failure. Handling both here means no component ever has
 * to render "[object Object]" at a user.
 */
async function readErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    const detail = data?.detail;

    if (typeof detail === "string") return detail;

    if (Array.isArray(detail)) {
      return detail
        .map((item: { loc?: unknown[]; msg?: string }) => {
          const field = item.loc?.slice(1).join(".");
          const message = item.msg ?? "is invalid";
          return field ? `${field}: ${message}` : message;
        })
        .join("; ");
    }
  } catch {
    // Not JSON - fall through to a generic message.
  }
  return `Request failed (${response.status})`;
}

/* ------------------------------------------------------------------ types */

export type UserRole = "owner" | "customer";
export type BookingStatus = "confirmed" | "cancelled" | "completed" | "no_show";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  created_at: string;
};

export type Token = {
  access_token: string;
  token_type: string;
};

export type Service = {
  id: number;
  name: string;
  duration_minutes: number;
  price: string;
  currency: string;
};

export type SlotList = {
  business_slug: string;
  service_id: number;
  date: string;
  timezone: string;
  duration_minutes: number;
  /** ISO 8601 strings in UTC. Convert for display; never assume the viewer's zone. */
  slots: string[];
};

export type Booking = {
  id: number;
  starts_at: string;
  ends_at: string;
  status: BookingStatus;
  access_token: string;
  service: Service;
  customer_name: string;
  customer_email: string;
};

/* --------------------------------------------------------------- endpoints */

export const api = {
  signup: (body: {
    email: string;
    password: string;
    full_name: string;
    role?: UserRole;
  }) => request<User>("/auth/signup", { method: "POST", body }),

  login: (body: { email: string; password: string }) =>
    request<Token>("/auth/login", { method: "POST", body }),

  me: (token: string) => request<User>("/auth/me", { token }),

  slots: (slug: string, serviceId: number, date: string) =>
    request<SlotList>(
      `/businesses/${encodeURIComponent(slug)}/slots?service_id=${serviceId}&date=${date}`,
    ),

  createBooking: (
    body: {
      business_slug: string;
      service_id: number;
      starts_at: string;
      guest_name?: string;
      guest_email?: string;
    },
    token?: string,
  ) => request<Booking>("/bookings", { method: "POST", body, token }),

  getBooking: (bookingToken: string) =>
    request<Booking>(`/bookings/${encodeURIComponent(bookingToken)}`),

  cancelBooking: (bookingToken: string) =>
    request<Booking>(`/bookings/${encodeURIComponent(bookingToken)}/cancel`, {
      method: "POST",
    }),
};
