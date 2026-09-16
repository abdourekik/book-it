"""Database reads shared by more than one router.

Deliberately thin: these fetch rows and nothing more. The rules about what the rows
*mean* live in app/domain, where they can be tested without a database.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AvailabilityRule,
    Booking,
    BookingStatus,
    Business,
    Service,
    TimeOff,
)


def get_business_by_slug(db: Session, slug: str) -> Business | None:
    return db.execute(select(Business).where(Business.slug == slug)).scalar_one_or_none()


def get_service(db: Session, business_id: int, service_id: int) -> Service | None:
    return db.execute(
        select(Service).where(Service.id == service_id, Service.business_id == business_id)
    ).scalar_one_or_none()


def local_day_bounds(timezone: str, on_date: date) -> tuple[datetime, datetime]:
    """The UTC instants that bracket one local calendar day.

    A "day" is a local idea. In Paris, 6 October runs from 22:00 UTC on the 5th to
    22:00 UTC on the 6th. Querying a UTC-midnight-to-midnight range instead would miss
    bookings at either end of the day.
    """
    zone = ZoneInfo(timezone)
    start = datetime.combine(on_date, time.min, tzinfo=zone).astimezone(UTC)
    end = datetime.combine(on_date + timedelta(days=1), time.min, tzinfo=zone).astimezone(UTC)
    return start, end


def availability_rules(db: Session, business_id: int) -> list[AvailabilityRule]:
    return list(
        db.execute(
            select(AvailabilityRule).where(AvailabilityRule.business_id == business_id)
        ).scalars()
    )


def bookings_overlapping(db: Session, business_id: int, start: datetime, end: datetime):
    """Confirmed bookings that touch the window [start, end).

    The comparison is `starts_at < end AND ends_at > start` - the same half-open overlap
    test used everywhere else in this codebase. A booking that merely ends exactly at
    `start` is outside the window.
    """
    return list(
        db.execute(
            select(Booking).where(
                Booking.business_id == business_id,
                Booking.status == BookingStatus.CONFIRMED,
                Booking.starts_at < end,
                Booking.ends_at > start,
            )
        ).scalars()
    )


def time_off_overlapping(db: Session, business_id: int, start: datetime, end: datetime):
    return list(
        db.execute(
            select(TimeOff).where(
                TimeOff.business_id == business_id,
                TimeOff.starts_at < end,
                TimeOff.ends_at > start,
            )
        ).scalars()
    )


def get_booking_by_token(db: Session, token: str) -> Booking | None:
    return db.execute(select(Booking).where(Booking.access_token == token)).scalar_one_or_none()
