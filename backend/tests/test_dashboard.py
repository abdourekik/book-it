"""Tests for the owner dashboard: upcoming bookings, stats, owner-side cancellation."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.stats import WEEKDAY_NAMES, postgres_dow_to_python, week_bounds
from app.models import Booking, BookingStatus

PARIS = "Europe/Paris"
PASSWORD = "a long enough password"


def auth(client, email: str, role: str) -> dict[str, str]:
    client.post(
        "/auth/signup",
        json={"email": email, "password": PASSWORD, "full_name": "Test", "role": role},
    )
    token = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def shop(client, db):
    """An owner with a business, one service, and open hours every day."""
    headers = auth(client, "joe@example.com", "owner")
    client.post(
        "/me/business",
        json={
            "name": "Joe's",
            "slug": "joes",
            "timezone": PARIS,
            "slot_interval_minutes": 30,
        },
        headers=headers,
    )
    service_id = client.post(
        "/me/services",
        json={"name": "Haircut", "duration_minutes": 30, "price": "25.00"},
        headers=headers,
    ).json()["id"]
    client.put(
        "/me/availability",
        json={
            "rules": [{"weekday": d, "start_time": "00:00", "end_time": "23:59"} for d in range(7)]
        },
        headers=headers,
    )
    business_id = client.get("/me/business", headers=headers).json()["id"]
    return {"headers": headers, "service_id": service_id, "business_id": business_id, "db": db}


def add_booking(db, shop, *, days_ahead: float, status=BookingStatus.CONFIRMED, minutes: int = 30):
    """Insert a booking directly, so tests can place one in the past if they need to."""
    starts = datetime.now(UTC) + timedelta(days=days_ahead)
    booking = Booking(
        business_id=shop["business_id"],
        service_id=shop["service_id"],
        guest_name="Guest",
        guest_email="guest@example.com",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=minutes),
        status=status,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


# ------------------------------------------------------- pure helpers


@pytest.mark.parametrize(
    ("postgres_dow", "expected"),
    [(0, "Sunday"), (1, "Monday"), (2, "Tuesday"), (6, "Saturday")],
)
def test_postgres_weekday_numbering_is_converted(postgres_dow, expected):
    """Postgres counts from Sunday, Python from Monday. Mixing them shifts everything."""
    assert WEEKDAY_NAMES[postgres_dow_to_python(postgres_dow)] == expected


def test_week_bounds_start_on_the_local_monday():
    # A Wednesday.
    start, end = week_bounds(PARIS, today=date(2026, 10, 7))

    local_start = start.astimezone(ZoneInfo(PARIS))
    assert local_start.date() == date(2026, 10, 5)  # the Monday
    assert local_start.time() == time(0, 0)
    assert end - start == timedelta(days=7)


def test_week_bounds_are_in_local_time_not_utc():
    """Paris midnight is 22:00 UTC the previous day, and the query must reflect that."""
    start, _ = week_bounds(PARIS, today=date(2026, 10, 7))

    assert start.tzinfo == UTC
    assert start.hour == 22  # 00:00 Paris (UTC+2) == 22:00 UTC on the Sunday


# -------------------------------------------------------- endpoints


def test_upcoming_bookings_lists_confirmed_appointments_in_order(client, shop, db):
    add_booking(db, shop, days_ahead=3)
    add_booking(db, shop, days_ahead=1)

    response = client.get("/me/bookings", headers=shop["headers"])

    assert response.status_code == 200
    starts = [b["starts_at"] for b in response.json()]
    assert starts == sorted(starts)  # soonest first


def test_upcoming_bookings_excludes_the_past(client, shop, db):
    add_booking(db, shop, days_ahead=-2)
    add_booking(db, shop, days_ahead=2)

    assert len(client.get("/me/bookings", headers=shop["headers"]).json()) == 1


def test_upcoming_bookings_excludes_cancelled(client, shop, db):
    add_booking(db, shop, days_ahead=2, status=BookingStatus.CANCELLED)

    assert client.get("/me/bookings", headers=shop["headers"]).json() == []


def test_upcoming_bookings_respects_the_days_window(client, shop, db):
    add_booking(db, shop, days_ahead=30)

    assert client.get("/me/bookings", headers=shop["headers"]).json() == []
    assert len(client.get("/me/bookings?days=60", headers=shop["headers"]).json()) == 1


def test_owner_bookings_never_expose_the_customer_access_token(client, shop, db):
    """The token authorises cancelling. It belongs to the customer, not the owner."""
    add_booking(db, shop, days_ahead=1)

    body = client.get("/me/bookings", headers=shop["headers"]).json()

    assert "access_token" not in body[0]


def test_customers_cannot_see_the_dashboard(client, shop):
    customer = auth(client, "sam@example.com", "customer")

    assert client.get("/me/bookings", headers=customer).status_code == 403
    assert client.get("/me/stats", headers=customer).status_code == 403


# ------------------------------------------------------------ stats


def test_stats_on_an_empty_business_are_zero_not_an_error(client, shop):
    body = client.get("/me/stats", headers=shop["headers"]).json()

    assert body["total_bookings"] == 0
    assert body["cancellation_rate"] == 0.0  # not a division by zero
    assert body["busiest_weekday"] is None


def test_cancellation_rate_counts_cancelled_over_total(client, shop, db):
    add_booking(db, shop, days_ahead=1)
    add_booking(db, shop, days_ahead=2)
    add_booking(db, shop, days_ahead=3, status=BookingStatus.CANCELLED)

    body = client.get("/me/stats", headers=shop["headers"]).json()

    assert body["total_bookings"] == 3
    assert body["cancellation_rate"] == pytest.approx(1 / 3, abs=1e-4)


def test_next_7_days_counts_only_the_coming_week(client, shop, db):
    add_booking(db, shop, days_ahead=2)
    add_booking(db, shop, days_ahead=20)

    assert client.get("/me/stats", headers=shop["headers"]).json()["bookings_next_7_days"] == 1


def test_busiest_weekday_is_reported_in_local_time(client, shop, db):
    """Three bookings on one weekday, one on another."""
    # Find a date at least a week out, then use the same weekday three times.
    base = datetime.now(UTC) + timedelta(days=8)
    for offset in (0, 7, 14):
        starts = base + timedelta(days=offset)
        db.add(
            Booking(
                business_id=shop["business_id"],
                service_id=shop["service_id"],
                guest_name="G",
                guest_email="g@example.com",
                starts_at=starts,
                ends_at=starts + timedelta(minutes=30),
            )
        )
    other = base + timedelta(days=1)
    db.add(
        Booking(
            business_id=shop["business_id"],
            service_id=shop["service_id"],
            guest_name="G",
            guest_email="g@example.com",
            starts_at=other,
            ends_at=other + timedelta(minutes=30),
        )
    )
    db.commit()

    body = client.get("/me/stats", headers=shop["headers"]).json()

    expected = WEEKDAY_NAMES[base.astimezone(ZoneInfo(PARIS)).weekday()]
    assert body["busiest_weekday"] == expected


# ------------------------------------------------- owner cancellation


def test_an_owner_can_cancel_a_booking_by_id(client, shop, db):
    booking = add_booking(db, shop, days_ahead=2)

    response = client.post(f"/me/bookings/{booking.id}/cancel", headers=shop["headers"])

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_owner_cancellation_is_idempotent(client, shop, db):
    booking = add_booking(db, shop, days_ahead=2)

    client.post(f"/me/bookings/{booking.id}/cancel", headers=shop["headers"])
    second = client.post(f"/me/bookings/{booking.id}/cancel", headers=shop["headers"])

    assert second.status_code == 200


def test_an_owner_cannot_cancel_another_businesss_booking(client, shop, db):
    booking = add_booking(db, shop, days_ahead=2)

    intruder = auth(client, "amira@example.com", "owner")
    client.post(
        "/me/business",
        json={"name": "Other", "slug": "other", "timezone": PARIS},
        headers=intruder,
    )

    response = client.post(f"/me/bookings/{booking.id}/cancel", headers=intruder)

    assert response.status_code == 404


# -------------------------------------------------- customer bookings


def test_a_customer_sees_only_their_own_bookings(client, shop, db):
    customer = auth(client, "sam@example.com", "customer")
    user_id = client.get("/auth/me", headers=customer).json()["id"]

    starts = datetime.now(UTC) + timedelta(days=3)
    db.add(
        Booking(
            business_id=shop["business_id"],
            service_id=shop["service_id"],
            customer_id=user_id,
            starts_at=starts,
            ends_at=starts + timedelta(minutes=30),
        )
    )
    add_booking(db, shop, days_ahead=4)  # a guest booking, belonging to nobody
    db.commit()

    body = client.get("/my/bookings", headers=customer).json()

    assert len(body) == 1
    assert body[0]["customer_name"] == "Test"


def test_my_bookings_requires_signing_in(client):
    assert client.get("/my/bookings").status_code == 401
