"""Create a demo business with services, hours, and bookings — through the API.

    python -m scripts.demo_data --api-url https://book-it-api-uxxh.onrender.com

Deliberately different from scripts/seed.py, which writes straight to the database and
refuses to run outside development. This one only uses the public API, so it is safe to
point at production: it can do nothing a customer with a browser could not do, and it
never needs the database password.

It is idempotent. Re-run it and it signs in to the existing demo account rather than
failing, so you can top up the bookings without starting over.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import secrets
import sys
import urllib.error
import urllib.request
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TIMEZONE = "Africa/Tunis"
SLUG = "demo-barbershop"

SERVICES = [
    {"name": "Haircut", "duration_minutes": 30, "price": "25.00", "currency": "TND"},
    {"name": "Beard trim", "duration_minutes": 20, "price": "12.00", "currency": "TND"},
    {"name": "Haircut + beard", "duration_minutes": 45, "price": "32.00", "currency": "TND"},
]

# Monday-Friday with a lunch break, shorter Saturday, closed Sunday.
HOURS = [
    *[{"weekday": d, "start_time": "09:00:00", "end_time": "12:00:00"} for d in range(5)],
    *[{"weekday": d, "start_time": "14:00:00", "end_time": "18:00:00"} for d in range(5)],
    {"weekday": 5, "start_time": "10:00:00", "end_time": "16:00:00"},
]

GUESTS = [
    ("Lea Moreau", "lea@example.com"),
    ("Karim Zouari", "karim@example.com"),
    ("Sam Carter", "sam@example.com"),
]


class ApiError(Exception):
    pass


def call(base: str, path: str, *, method: str = "GET", body=None, token=None):
    request = urllib.request.Request(
        f"{base.rstrip('/')}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            **({"Content-Type": "application/json"} if body is not None else {}),
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        # FastAPI errors are JSON with a "detail" field; anything else (a proxy page, a
        # gateway timeout) is plain text and is shown as-is.
        with contextlib.suppress(json.JSONDecodeError, AttributeError):
            detail = json.loads(detail).get("detail", detail)
        raise ApiError(f"{method} {path} -> {exc.code}: {detail}") from None
    except urllib.error.URLError as exc:
        raise ApiError(f"Could not reach {base}: {exc.reason}") from None


def next_weekday(weekday: int, weeks_ahead: int = 0) -> date:
    today = datetime.now(UTC).astimezone(ZoneInfo(TIMEZONE)).date()
    days = (weekday - today.weekday()) % 7 or 7
    return today + timedelta(days=days + 7 * weeks_ahead)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-url", required=True, help="e.g. https://book-it-api-xxxx.onrender.com"
    )
    parser.add_argument("--email", default="demo-owner@example.com")
    parser.add_argument(
        "--password",
        default=None,
        help="Omit to generate one and print it here (it is never sent anywhere else).",
    )
    args = parser.parse_args()

    base = args.api_url
    password = args.password or secrets.token_urlsafe(16)

    print(f"API: {base}")
    print("Waking the service (a free-tier cold start takes up to a minute)...")
    health = call(base, "/health")
    print(f"  {health}\n")

    # --- owner account ------------------------------------------------------
    try:
        call(
            base,
            "/auth/signup",
            method="POST",
            body={
                "email": args.email,
                "password": password,
                "full_name": "Demo Owner",
                "role": "owner",
            },
        )
        print(f"Created owner {args.email}")
        print(f"  PASSWORD: {password}")
        print("  ^ save this now; it is not stored anywhere and cannot be recovered\n")
    except ApiError as exc:
        if "already exists" not in str(exc):
            raise
        if args.password is None:
            print(f"An account for {args.email} already exists.")
            print("Re-run with --password YOUR_PASSWORD to add data to it.")
            return 1
        print(f"Using the existing account {args.email}\n")

    token = call(
        base, "/auth/login", method="POST", body={"email": args.email, "password": password}
    )["access_token"]

    # --- business -----------------------------------------------------------
    try:
        call(
            base,
            "/me/business",
            method="POST",
            token=token,
            body={
                "name": "Demo Barbershop",
                "slug": SLUG,
                "timezone": TIMEZONE,
                "description": "A sample business, created to show what Book-it looks like in use.",
                "slot_interval_minutes": 15,
            },
        )
        print("Created business 'Demo Barbershop'")
    except ApiError as exc:
        if "already have" not in str(exc) and "taken" not in str(exc):
            raise
        print("Business already exists, reusing it")

    # --- services -----------------------------------------------------------
    existing = {s["name"] for s in call(base, "/me/services", token=token)}
    for service in SERVICES:
        if service["name"] in existing:
            continue
        call(base, "/me/services", method="POST", token=token, body=service)
    services = [s for s in call(base, "/me/services", token=token) if s["is_active"]]
    print(f"Services: {', '.join(s['name'] for s in services)}")

    # --- opening hours ------------------------------------------------------
    call(base, "/me/availability", method="PUT", token=token, body={"rules": HOURS})
    print("Opening hours: Mon-Fri 09:00-12:00 and 14:00-18:00, Sat 10:00-16:00")

    # --- a day off ----------------------------------------------------------
    friday = next_weekday(4, weeks_ahead=1)
    zone = ZoneInfo(TIMEZONE)
    try:
        call(
            base,
            "/me/time-off",
            method="POST",
            token=token,
            body={
                "starts_at": datetime.combine(friday, time.min, tzinfo=zone).isoformat(),
                "ends_at": datetime.combine(
                    friday + timedelta(days=1), time.min, tzinfo=zone
                ).isoformat(),
                "reason": "Family wedding",
            },
        )
        print(f"Time off: all day {friday}")
    except ApiError as exc:
        print(f"Time off skipped ({exc})")

    # --- bookings -----------------------------------------------------------
    # Booked as guests, through the same endpoint a real customer uses.
    tuesday = next_weekday(1)
    haircut = next(s for s in services if s["name"] == "Haircut")
    slots = call(
        base, f"/businesses/{SLUG}/slots?service_id={haircut['id']}&date={tuesday.isoformat()}"
    )["slots"]

    if not slots:
        print(f"No slots on {tuesday} - skipping demo bookings")
    else:
        made = 0
        # Spread them out so the day does not look artificially packed.
        for (name, email), index in zip(GUESTS, (4, 12, 20), strict=False):
            if index >= len(slots):
                continue
            try:
                call(
                    base,
                    "/bookings",
                    method="POST",
                    body={
                        "business_slug": SLUG,
                        "service_id": haircut["id"],
                        "starts_at": slots[index],
                        "guest_name": name,
                        "guest_email": email,
                    },
                )
                made += 1
            except ApiError as exc:
                if "just taken" not in str(exc) and "not available" not in str(exc):
                    raise
        print(f"Bookings: {made} on {tuesday}")

    # --- where to look ------------------------------------------------------
    print("\nDone. Open these:")
    print(f"  Public booking page : {base.replace('book-it-api', 'BOOKING-SITE')}")
    print(f"    -> on your frontend: /b/{SLUG}")
    print(f"  Owner dashboard     : sign in as {args.email}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ApiError as exc:
        print(f"\nFailed: {exc}", file=sys.stderr)
        sys.exit(1)
