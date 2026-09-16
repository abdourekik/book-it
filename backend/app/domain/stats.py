"""Owner dashboard statistics.

Every figure here is computed in the business's own timezone. "Bookings this week" means
the week as the owner experiences it, not a UTC week that starts on Sunday evening for a
shop in Paris.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus

# PostgreSQL's EXTRACT(DOW) returns 0 for Sunday; Python's weekday() returns 0 for
# Monday, which is what AvailabilityRule uses. Mixing them shifts every schedule by a
# day, so the conversion happens in exactly one place: here.
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def postgres_dow_to_python(dow: int) -> int:
    """0=Sunday..6=Saturday  ->  0=Monday..6=Sunday."""
    return (dow - 1) % 7


@dataclass
class Stats:
    bookings_this_week: int
    bookings_next_7_days: int
    cancellation_rate: float
    busiest_weekday: str | None
    total_bookings: int


def week_bounds(timezone: str, today: date | None = None) -> tuple[datetime, datetime]:
    """Monday 00:00 to next Monday 00:00, in the business's timezone, returned as UTC."""
    zone = ZoneInfo(timezone)
    today = today or datetime.now(UTC).astimezone(zone).date()

    monday = today - timedelta(days=today.weekday())
    start = datetime.combine(monday, time.min, tzinfo=zone).astimezone(UTC)
    end = datetime.combine(monday + timedelta(days=7), time.min, tzinfo=zone).astimezone(UTC)
    return start, end


def compute_stats(db: Session, business_id: int, timezone: str) -> Stats:
    """All five figures, in four queries."""
    now = datetime.now(UTC)
    week_start, week_end = week_bounds(timezone)

    bookings_this_week = db.execute(
        select(func.count())
        .select_from(Booking)
        .where(
            Booking.business_id == business_id,
            Booking.status == BookingStatus.CONFIRMED,
            Booking.starts_at >= week_start,
            Booking.starts_at < week_end,
        )
    ).scalar_one()

    bookings_next_7_days = db.execute(
        select(func.count())
        .select_from(Booking)
        .where(
            Booking.business_id == business_id,
            Booking.status == BookingStatus.CONFIRMED,
            Booking.starts_at >= now,
            Booking.starts_at < now + timedelta(days=7),
        )
    ).scalar_one()

    # One pass for both totals: counting cancelled and total separately would be two
    # queries returning figures that could disagree if a row changed between them.
    totals = db.execute(
        select(
            func.count().label("total"),
            func.count(case((Booking.status == BookingStatus.CANCELLED, 1))).label("cancelled"),
        ).where(Booking.business_id == business_id)
    ).one()

    cancellation_rate = (totals.cancelled / totals.total) if totals.total else 0.0

    # AT TIME ZONE converts the stored UTC instant to local wall-clock before extracting
    # the day, so a 00:30 Tuesday appointment in Paris counts as Tuesday and not as the
    # Monday it still is in UTC.
    local = func.timezone(timezone, Booking.starts_at)
    busiest_row = db.execute(
        select(func.extract("dow", local).label("dow"), func.count().label("n"))
        .where(
            Booking.business_id == business_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]),
        )
        .group_by("dow")
        .order_by(func.count().desc())
        .limit(1)
    ).first()

    busiest_weekday = (
        WEEKDAY_NAMES[postgres_dow_to_python(int(busiest_row.dow))] if busiest_row else None
    )

    return Stats(
        bookings_this_week=bookings_this_week,
        bookings_next_7_days=bookings_next_7_days,
        cancellation_rate=round(cancellation_rate, 4),
        busiest_weekday=busiest_weekday,
        total_bookings=totals.total,
    )
