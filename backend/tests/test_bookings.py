"""Tests for the booking endpoints, and for double-booking under real concurrency."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import (
    AvailabilityRule,
    Booking,
    BookingStatus,
    Business,
    Service,
    User,
    UserRole,
)

PARIS = "Europe/Paris"
SLUG = "test-barber"


def next_tuesday(weeks: int = 1):
    """A Tuesday safely in the future, so 'is it in the past?' never interferes."""
    today = datetime.now(UTC).date()
    days = (1 - today.weekday()) % 7 or 7
    return today + timedelta(days=days + 7 * weeks)


def at_local(day, hhmm: str) -> datetime:
    return datetime.combine(day, time.fromisoformat(hhmm), tzinfo=ZoneInfo(PARIS)).astimezone(UTC)


@pytest.fixture
def shop(db: Session):
    """A barber open Tuesdays 09:00-17:00 local, with one 30-minute service."""
    owner = User(
        email="owner@example.com",
        password_hash="x",
        full_name="Owner",
        role=UserRole.OWNER,
    )
    db.add(owner)
    db.flush()

    business = Business(
        owner_id=owner.id, name="Test Barber", slug=SLUG, timezone=PARIS, slot_interval_minutes=30
    )
    db.add(business)
    db.flush()

    service = Service(
        business_id=business.id, name="Haircut", duration_minutes=30, price=Decimal("25.00")
    )
    db.add(service)
    db.add(
        AvailabilityRule(
            business_id=business.id,
            weekday=1,  # Tuesday
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
    )
    db.commit()

    return {"business": business, "service": service, "day": next_tuesday()}


def guest_booking(shop, hhmm: str = "10:00") -> dict:
    return {
        "business_slug": SLUG,
        "service_id": shop["service"].id,
        "starts_at": at_local(shop["day"], hhmm).isoformat(),
        "guest_name": "Lea Moreau",
        "guest_email": "lea@example.com",
    }


# ------------------------------------------------------------- slots


def test_slots_are_listed_without_logging_in(client, shop):
    response = client.get(
        f"/businesses/{SLUG}/slots",
        params={"service_id": shop["service"].id, "date": shop["day"].isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == PARIS
    assert body["duration_minutes"] == 30
    assert len(body["slots"]) == 16  # 09:00 to 16:30 in 30-minute steps


def test_slots_for_an_unknown_business_are_404(client, shop):
    response = client.get(
        "/businesses/nope/slots",
        params={"service_id": shop["service"].id, "date": shop["day"].isoformat()},
    )

    assert response.status_code == 404


def test_a_booking_removes_its_slot_from_the_list(client, shop):
    client.post("/bookings", json=guest_booking(shop, "10:00"))

    response = client.get(
        f"/businesses/{SLUG}/slots",
        params={"service_id": shop["service"].id, "date": shop["day"].isoformat()},
    )

    taken = at_local(shop["day"], "10:00")
    assert all(datetime.fromisoformat(s) != taken for s in response.json()["slots"])


# ----------------------------------------------------------- booking


def test_a_guest_can_book(client, shop):
    response = client.post("/bookings", json=guest_booking(shop))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["customer_name"] == "Lea Moreau"
    assert body["service"]["name"] == "Haircut"
    assert len(body["access_token"]) > 20  # the cancellation handle


def test_a_signed_in_customer_can_book(client, shop):
    client.post(
        "/auth/signup",
        json={"email": "sam@example.com", "password": "a long enough password", "full_name": "Sam"},
    )
    token = client.post(
        "/auth/login", json={"email": "sam@example.com", "password": "a long enough password"}
    ).json()["access_token"]

    payload = guest_booking(shop)
    payload.pop("guest_name")
    payload.pop("guest_email")

    response = client.post("/bookings", json=payload, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 201
    assert response.json()["customer_name"] == "Sam"


def test_booking_without_guest_details_or_a_login_is_rejected(client, shop):
    payload = guest_booking(shop)
    payload.pop("guest_name")
    payload.pop("guest_email")

    assert client.post("/bookings", json=payload).status_code == 400


def test_guest_name_without_email_is_rejected(client, shop):
    payload = guest_booking(shop)
    payload.pop("guest_email")

    assert client.post("/bookings", json=payload).status_code == 422


def test_a_naive_datetime_is_rejected(client, shop):
    """ "10:00" with no offset is ambiguous, and guessing is how bookings end up wrong."""
    payload = guest_booking(shop)
    payload["starts_at"] = f"{shop['day'].isoformat()}T10:00:00"

    response = client.post("/bookings", json=payload)

    assert response.status_code == 422
    assert "timezone offset" in str(response.json())


def test_booking_outside_opening_hours_is_rejected(client, shop):
    response = client.post("/bookings", json=guest_booking(shop, "20:00"))

    assert response.status_code == 409
    assert "not available" in response.json()["detail"]


def test_booking_a_taken_slot_is_rejected(client, shop):
    assert client.post("/bookings", json=guest_booking(shop, "10:00")).status_code == 201

    second = client.post("/bookings", json=guest_booking(shop, "10:00"))

    assert second.status_code == 409


def test_booking_in_the_past_is_rejected(client, shop):
    payload = guest_booking(shop)
    payload["starts_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()

    assert client.post("/bookings", json=payload).status_code == 409


def test_back_to_back_bookings_are_allowed(client, shop):
    """10:00-10:30 and 10:30-11:00 do not overlap."""
    assert client.post("/bookings", json=guest_booking(shop, "10:00")).status_code == 201
    assert client.post("/bookings", json=guest_booking(shop, "10:30")).status_code == 201


# ----------------------------------------------- view, cancel, reschedule


def test_a_booking_can_be_fetched_with_its_token(client, shop):
    token = client.post("/bookings", json=guest_booking(shop)).json()["access_token"]

    response = client.get(f"/bookings/{token}")

    assert response.status_code == 200
    assert response.json()["customer_name"] == "Lea Moreau"


def test_an_unknown_token_is_404_not_403(client, shop):
    """Confirming a token exists but is not yours would help someone guess them."""
    assert client.get("/bookings/definitely-not-a-real-token").status_code == 404


def test_cancelling_frees_the_slot(client, shop):
    token = client.post("/bookings", json=guest_booking(shop, "10:00")).json()["access_token"]

    cancelled = client.post(f"/bookings/{token}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    # The same time is bookable again - which is the entire point of cancelling.
    assert client.post("/bookings", json=guest_booking(shop, "10:00")).status_code == 201


def test_cancelling_twice_is_harmless(client, shop):
    """Clicking the emailed link twice must not produce an error."""
    token = client.post("/bookings", json=guest_booking(shop)).json()["access_token"]

    assert client.post(f"/bookings/{token}/cancel").status_code == 200
    assert client.post(f"/bookings/{token}/cancel").status_code == 200


def test_a_booking_can_be_moved(client, shop):
    token = client.post("/bookings", json=guest_booking(shop, "10:00")).json()["access_token"]

    response = client.post(
        f"/bookings/{token}/reschedule",
        json={"starts_at": at_local(shop["day"], "14:00").isoformat()},
    )

    assert response.status_code == 200
    assert datetime.fromisoformat(response.json()["starts_at"]) == at_local(shop["day"], "14:00")


def test_moving_onto_a_taken_slot_is_rejected(client, shop):
    first = client.post("/bookings", json=guest_booking(shop, "10:00")).json()["access_token"]
    client.post("/bookings", json=guest_booking(shop, "11:00"))

    response = client.post(
        f"/bookings/{first}/reschedule",
        json={"starts_at": at_local(shop["day"], "11:00").isoformat()},
    )

    assert response.status_code == 409


def test_a_booking_can_be_moved_onto_its_own_time(client, shop):
    """Its own span must not block it - otherwise nudging 10:00 to 10:30 fails."""
    token = client.post("/bookings", json=guest_booking(shop, "10:00")).json()["access_token"]

    response = client.post(
        f"/bookings/{token}/reschedule",
        json={"starts_at": at_local(shop["day"], "10:30").isoformat()},
    )

    assert response.status_code == 200


def test_a_cancelled_booking_cannot_be_moved(client, shop):
    token = client.post("/bookings", json=guest_booking(shop)).json()["access_token"]
    client.post(f"/bookings/{token}/cancel")

    response = client.post(
        f"/bookings/{token}/reschedule",
        json={"starts_at": at_local(shop["day"], "14:00").isoformat()},
    )

    assert response.status_code == 409


# --------------------------------------------------------- concurrency


def test_only_one_of_many_simultaneous_bookings_succeeds(engine):
    """The test this whole design exists for.

    Ten threads, ten real database connections, all inserting the SAME slot at the same
    moment. A threading.Barrier holds them until every one is ready, so they race for
    real rather than politely queueing.

    This test cannot use the rolled-back `db` fixture: a transaction that is never
    committed is invisible to other connections, so nothing would ever conflict. It
    manages its own committed data and cleans up afterwards.

    Exactly one insert must win. Not "usually one" - the exclusion constraint makes it
    a guarantee, and this asserts the guarantee rather than hoping.
    """
    threads = 10
    results: list[str] = []
    lock = threading.Lock()
    barrier = threading.Barrier(threads)

    setup = Session(bind=engine)
    owner = User(email="race@example.com", password_hash="x", full_name="Race", role=UserRole.OWNER)
    setup.add(owner)
    setup.flush()
    business = Business(owner_id=owner.id, name="Race", slug="race-shop", timezone=PARIS)
    setup.add(business)
    setup.flush()
    service = Service(
        business_id=business.id, name="Cut", duration_minutes=30, price=Decimal("10.00")
    )
    setup.add(service)
    setup.commit()

    business_id, service_id = business.id, service.id
    owner_id = owner.id
    starts_at = at_local(next_tuesday(2), "10:00")

    def attempt(n: int) -> None:
        session = Session(bind=engine)
        try:
            booking = Booking(
                business_id=business_id,
                service_id=service_id,
                guest_name=f"Racer {n}",
                guest_email=f"racer{n}@example.com",
                starts_at=starts_at,
                ends_at=starts_at + timedelta(minutes=30),
                status=BookingStatus.CONFIRMED,
            )
            session.add(booking)
            barrier.wait(timeout=10)  # everyone goes at once
            session.commit()
            with lock:
                results.append("won")
        except DBAPIError:
            # Losing takes two forms, and both count. An ExclusionViolation means the
            # winner had already committed. A DeadlockDetected (40P01) means several
            # transactions piled up waiting on each other and PostgreSQL shot some of
            # them. Catching only IntegrityError here would let deadlocked threads die
            # silently and the assertion below would report a phantom result.
            session.rollback()
            with lock:
                results.append("lost")
        finally:
            session.close()

    workers = [threading.Thread(target=attempt, args=(n,)) for n in range(threads)]
    try:
        for w in workers:
            w.start()
        for w in workers:
            w.join(timeout=30)

        assert results.count("won") == 1, f"expected exactly one winner, got {results}"
        assert results.count("lost") == threads - 1

        check = Session(bind=engine)
        confirmed = (
            check.query(Booking)
            .filter(Booking.business_id == business_id, Booking.status == BookingStatus.CONFIRMED)
            .count()
        )
        check.close()
        assert confirmed == 1
    finally:
        cleanup = Session(bind=engine)
        cleanup.query(Booking).filter(Booking.business_id == business_id).delete()
        cleanup.query(Service).filter(Service.business_id == business_id).delete()
        cleanup.query(Business).filter(Business.id == business_id).delete()
        cleanup.query(User).filter(User.id == owner_id).delete()
        cleanup.commit()
        cleanup.close()
