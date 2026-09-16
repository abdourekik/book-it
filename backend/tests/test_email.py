"""Tests for transactional email and the reminder job."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core import email
from app.models import Booking, BookingStatus, Business, Service, User, UserRole
from scripts.send_reminders import send_all

PARIS = "Europe/Paris"


class RecordingSender:
    """Captures emails instead of sending them, so assertions can read the content."""

    name = "recording"

    def __init__(self) -> None:
        self.sent: list[email.Email] = []

    def send(self, message: email.Email) -> None:
        self.sent.append(message)


@pytest.fixture
def outbox():
    """Replace the process-wide sender for one test, then put it back."""
    original = email.get_sender()
    recorder = RecordingSender()
    email.set_sender(recorder)
    yield recorder
    email.set_sender(original)


@pytest.fixture
def shop(db):
    owner = User(email="joe@example.com", password_hash="x", full_name="Joe", role=UserRole.OWNER)
    db.add(owner)
    db.flush()
    business = Business(owner_id=owner.id, name="Joe's", slug="joes-mail", timezone=PARIS)
    db.add(business)
    db.flush()
    service = Service(
        business_id=business.id, name="Haircut", duration_minutes=30, price=Decimal("25.00")
    )
    db.add(service)
    db.commit()
    return {"business": business, "service": service}


def make_booking(db, shop, *, hours_ahead: float, status=BookingStatus.CONFIRMED, reminded=False):
    starts = datetime.now(UTC) + timedelta(hours=hours_ahead)
    booking = Booking(
        business_id=shop["business"].id,
        service_id=shop["service"].id,
        guest_name="Lea Moreau",
        guest_email="lea@example.com",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
        status=status,
        reminder_sent_at=datetime.now(UTC) if reminded else None,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


# --------------------------------------------------------- templates


def test_confirmation_email_contains_the_essentials():
    message = email.booking_confirmation(
        to="lea@example.com",
        customer_name="Lea",
        business_name="Joe's",
        service_name="Haircut",
        starts_at=datetime(2026, 10, 6, 8, 0, tzinfo=UTC),
        timezone=PARIS,
        manage_url="https://book-it.app/bookings/abc123",
    )

    assert message.to == "lea@example.com"
    assert "Joe's" in message.subject
    assert "Haircut" in message.html
    assert "https://book-it.app/bookings/abc123" in message.html


def test_email_times_are_rendered_in_the_business_timezone():
    """08:00 UTC is 10:00 in Paris. An email showing 08:00 would send someone late."""
    message = email.booking_confirmation(
        to="x@example.com",
        customer_name="X",
        business_name="Joe's",
        service_name="Haircut",
        starts_at=datetime(2026, 10, 6, 8, 0, tzinfo=UTC),
        timezone=PARIS,
        manage_url="https://example.com",
    )

    assert "10:00" in message.subject
    assert "Europe/Paris" in message.subject
    assert "08:00" not in message.subject


def test_a_failing_sender_does_not_raise():
    """A broken email provider must never break a booking that already committed."""

    class Broken:
        name = "broken"

        def send(self, message):
            raise RuntimeError("provider is down")

    original = email.get_sender()
    email.set_sender(Broken())
    try:
        email.send(email.Email(to="a@b.com", subject="s", html="<p>x</p>"))  # must not raise
    finally:
        email.set_sender(original)


# -------------------------------------------------------- endpoints


def test_cancelling_sends_an_email(client, db, shop, outbox):
    """The `client` fixture is wired to the same `db` session, so a row made here is
    visible to the endpoint."""
    booking = make_booking(db, shop, hours_ahead=72)

    response = client.post(f"/bookings/{booking.access_token}/cancel")

    assert response.status_code == 200
    assert len(outbox.sent) == 1
    assert "cancelled" in outbox.sent[0].subject.lower()
    assert outbox.sent[0].to == "lea@example.com"


def test_booking_through_the_api_sends_a_confirmation(client, db, shop, outbox):
    from datetime import time

    from app.models import AvailabilityRule

    # Open every day, so any future time is bookable.
    db.add_all(
        AvailabilityRule(
            business_id=shop["business"].id,
            weekday=d,
            start_time=time(0, 0),
            end_time=time(23, 59),
        )
        for d in range(7)
    )
    db.commit()

    day = (datetime.now(UTC) + timedelta(days=3)).date()
    slots = client.get(
        f"/businesses/{shop['business'].slug}/slots",
        params={"service_id": shop["service"].id, "date": day.isoformat()},
    ).json()["slots"]

    response = client.post(
        "/bookings",
        json={
            "business_slug": shop["business"].slug,
            "service_id": shop["service"].id,
            "starts_at": slots[100],
            "guest_name": "Lea Moreau",
            "guest_email": "lea@example.com",
        },
    )

    assert response.status_code == 201
    assert len(outbox.sent) == 1
    assert "confirmed" in outbox.sent[0].subject.lower()
    # The capability URL must be in the email - it is the guest's only handle.
    assert response.json()["access_token"] in outbox.sent[0].html


# -------------------------------------------------------- reminders


def test_reminders_go_out_for_appointments_in_24_hours(db, shop, outbox):
    make_booking(db, shop, hours_ahead=24)

    sent = send_all(db)

    assert sent == 1
    assert len(outbox.sent) == 1
    assert "Tomorrow" in outbox.sent[0].subject


def test_appointments_outside_the_window_are_skipped(db, shop, outbox):
    make_booking(db, shop, hours_ahead=5)  # too soon
    make_booking(db, shop, hours_ahead=100)  # too far

    assert send_all(db) == 0
    assert outbox.sent == []


def test_cancelled_bookings_get_no_reminder(db, shop, outbox):
    make_booking(db, shop, hours_ahead=24, status=BookingStatus.CANCELLED)

    assert send_all(db) == 0


def test_a_reminder_is_never_sent_twice(db, shop, outbox):
    """The property that makes the cron safe to run hourly."""
    make_booking(db, shop, hours_ahead=24)

    assert send_all(db) == 1
    assert send_all(db) == 0  # second run finds nothing
    assert len(outbox.sent) == 1


def test_sending_stamps_the_booking(db, shop, outbox):
    booking = make_booking(db, shop, hours_ahead=24)
    assert booking.reminder_sent_at is None

    send_all(db)
    db.refresh(booking)

    assert booking.reminder_sent_at is not None


def test_dry_run_sends_nothing_and_stamps_nothing(db, shop, outbox):
    booking = make_booking(db, shop, hours_ahead=24)

    count = send_all(db, dry_run=True)
    db.refresh(booking)

    assert count == 1  # it reports what it would do
    assert outbox.sent == []
    assert booking.reminder_sent_at is None
