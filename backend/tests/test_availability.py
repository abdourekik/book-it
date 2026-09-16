"""Tests for slot availability - the core of the application.

Written before the implementation, on purpose. Every test states a rule a real barber
would recognise, and the function has to satisfy all of them at once.

No database here: available_slots() is a pure function over data, so these run in
milliseconds and fail for exactly one reason.
"""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.domain.availability import Interval, available_slots
from app.models import AvailabilityRule, Booking, BookingStatus, Business, Service, TimeOff

PARIS = "Europe/Paris"
TUNIS = "Africa/Tunis"

# A Tuesday, comfortably inside central European summer time (UTC+2 in Paris).
TUESDAY = date(2026, 10, 6)
MONDAY, TUESDAY_IDX = 0, 1


def business(tz: str = PARIS, interval: int = 30) -> Business:
    return Business(
        name="Test", slug="test", timezone=tz, slot_interval_minutes=interval, owner_id=1
    )


def service(minutes: int = 30, active: bool = True) -> Service:
    return Service(
        name="Test service",
        duration_minutes=minutes,
        price=Decimal("10.00"),
        is_active=active,
        business_id=1,
    )


def rule(start: str, end: str, weekday: int = TUESDAY_IDX) -> AvailabilityRule:
    return AvailabilityRule(
        weekday=weekday,
        start_time=time.fromisoformat(start),
        end_time=time.fromisoformat(end),
        business_id=1,
    )


def utc(tz: str, day: date, at: str) -> datetime:
    """The UTC instant of a local wall-clock time."""
    return datetime.combine(day, time.fromisoformat(at), tzinfo=ZoneInfo(tz)).astimezone(UTC)


def booking(start: str, minutes: int, status=BookingStatus.CONFIRMED, tz: str = PARIS) -> Booking:
    starts = utc(tz, TUESDAY, start)
    return Booking(
        starts_at=starts,
        ends_at=starts + timedelta(minutes=minutes),
        status=status,
        business_id=1,
        service_id=1,
        guest_name="X",
        guest_email="x@example.com",
    )


def local_times(slots: list[datetime], tz: str = PARIS) -> list[str]:
    """UTC results rendered as local HH:MM, so assertions are readable."""
    return [s.astimezone(ZoneInfo(tz)).strftime("%H:%M") for s in slots]


# ---------------------------------------------------- interval algebra
#
# Interval.overlaps is currently reached only through Interval.minus, which happens to
# compute the right pieces even if overlaps() is wrong. These tests pin the contract
# directly, because booking creation will call overlaps() on its own - and there, a
# half-open boundary error would reject every back-to-back appointment.


def at(hhmm: str) -> datetime:
    return datetime.combine(TUESDAY, time.fromisoformat(hhmm), tzinfo=UTC)


def iv(start: str, end: str) -> Interval:
    return Interval(at(start), at(end))


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (iv("09:00", "10:00"), iv("09:30", "10:30"), True),  # partial
        (iv("09:00", "10:00"), iv("09:15", "09:45"), True),  # contained
        (iv("09:15", "09:45"), iv("09:00", "10:00"), True),  # containing
        (iv("09:00", "10:00"), iv("09:00", "10:00"), True),  # identical
        (iv("09:00", "10:00"), iv("10:00", "11:00"), False),  # touching, after
        (iv("10:00", "11:00"), iv("09:00", "10:00"), False),  # touching, before
        (iv("09:00", "10:00"), iv("11:00", "12:00"), False),  # disjoint
    ],
    ids=[
        "partial",
        "contained",
        "containing",
        "identical",
        "touching after",
        "touching before",
        "disjoint",
    ],
)
def test_overlaps_treats_intervals_as_half_open(a, b, expected):
    assert a.overlaps(b) is expected
    assert b.overlaps(a) is expected  # the relation is symmetric


def test_minus_leaves_a_hole_in_the_middle():
    assert iv("09:00", "12:00").minus(iv("10:00", "11:00")) == [
        iv("09:00", "10:00"),
        iv("11:00", "12:00"),
    ]


def test_minus_a_covering_interval_leaves_nothing():
    assert iv("09:00", "10:00").minus(iv("08:00", "11:00")) == []


def test_minus_a_touching_interval_changes_nothing():
    assert iv("09:00", "10:00").minus(iv("10:00", "11:00")) == [iv("09:00", "10:00")]


# ------------------------------------------------------- opening hours


def test_closed_when_no_rule_covers_that_weekday():
    slots = available_slots(
        business=business(),
        service=service(),
        on_date=TUESDAY,
        rules=[rule("09:00", "17:00", weekday=MONDAY)],
    )

    assert slots == []


def test_simple_window_is_divided_by_the_slot_interval():
    slots = available_slots(
        business=business(interval=30),
        service=service(minutes=30),
        on_date=TUESDAY,
        rules=[rule("09:00", "11:00")],
    )

    assert local_times(slots) == ["09:00", "09:30", "10:00", "10:30"]


def test_a_service_must_finish_before_closing_time():
    """11:00 is not offered for a 60-minute service that closes at 11:30."""
    slots = available_slots(
        business=business(interval=30),
        service=service(minutes=60),
        on_date=TUESDAY,
        rules=[rule("09:00", "11:30")],
    )

    assert local_times(slots) == ["09:00", "09:30", "10:00", "10:30"]


def test_service_longer_than_the_window_yields_nothing():
    slots = available_slots(
        business=business(),
        service=service(minutes=120),
        on_date=TUESDAY,
        rules=[rule("09:00", "10:00")],
    )

    assert slots == []


def test_lunch_break_produces_two_separate_blocks():
    """Two rules on one weekday, and nothing offered across the gap."""
    slots = available_slots(
        business=business(interval=60),
        service=service(minutes=60),
        on_date=TUESDAY,
        rules=[rule("09:00", "12:00"), rule("14:00", "17:00")],
    )

    assert local_times(slots) == ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]


def test_an_inactive_service_is_not_bookable():
    slots = available_slots(
        business=business(),
        service=service(active=False),
        on_date=TUESDAY,
        rules=[rule("09:00", "17:00")],
    )

    assert slots == []


# ----------------------------------------------------------- bookings


def test_an_existing_booking_blocks_its_own_span():
    slots = available_slots(
        business=business(interval=30),
        service=service(minutes=30),
        on_date=TUESDAY,
        rules=[rule("09:00", "11:00")],
        bookings=[booking("09:30", 30)],
    )

    assert local_times(slots) == ["09:00", "10:00", "10:30"]


def test_back_to_back_booking_is_allowed():
    """A booking ending at 10:00 must not stop a new one starting at 10:00.

    Ranges are half-open - [09:30, 10:00) and [10:00, 10:30) touch without overlapping.
    Getting this wrong costs a barber half their bookable day.
    """
    slots = available_slots(
        business=business(interval=30),
        service=service(minutes=30),
        on_date=TUESDAY,
        rules=[rule("09:00", "11:00")],
        bookings=[booking("09:30", 30)],
    )

    assert "10:00" in local_times(slots)


def test_a_cancelled_booking_blocks_nothing():
    """Otherwise cancelling would not actually free the slot."""
    slots = available_slots(
        business=business(interval=30),
        service=service(minutes=30),
        on_date=TUESDAY,
        rules=[rule("09:00", "11:00")],
        bookings=[booking("09:30", 30, status=BookingStatus.CANCELLED)],
    )

    assert local_times(slots) == ["09:00", "09:30", "10:00", "10:30"]


def test_a_booking_blocks_every_slot_it_overlaps():
    """A 30-minute service cannot start at 09:45 if 10:00-10:30 is taken."""
    slots = available_slots(
        business=business(interval=15),
        service=service(minutes=30),
        on_date=TUESDAY,
        rules=[rule("09:00", "11:00")],
        bookings=[booking("10:00", 30)],
    )

    times = local_times(slots)
    assert "09:45" not in times  # would run into the booking
    assert "10:15" not in times  # starts inside the booking
    assert "10:30" in times  # starts exactly as it ends


# ----------------------------------------------------------- time off


def test_a_full_day_off_removes_everything():
    slots = available_slots(
        business=business(),
        service=service(),
        on_date=TUESDAY,
        rules=[rule("09:00", "17:00")],
        time_off=[
            TimeOff(
                starts_at=utc(PARIS, TUESDAY, "00:00"),
                ends_at=utc(PARIS, TUESDAY + timedelta(days=1), "00:00"),
                business_id=1,
            )
        ],
    )

    assert slots == []


def test_a_partial_day_off_removes_only_that_part():
    slots = available_slots(
        business=business(interval=60),
        service=service(minutes=60),
        on_date=TUESDAY,
        rules=[rule("09:00", "13:00")],
        time_off=[
            TimeOff(
                starts_at=utc(PARIS, TUESDAY, "10:00"),
                ends_at=utc(PARIS, TUESDAY, "12:00"),
                business_id=1,
            )
        ],
    )

    assert local_times(slots) == ["09:00", "12:00"]


# ---------------------------------------------------------- timezones


def test_the_same_local_hour_is_a_different_instant_in_each_timezone():
    """Paris is UTC+2 and Tunis UTC+1 in October - a one-hour difference."""
    common = dict(service=service(minutes=60), on_date=TUESDAY, rules=[rule("09:00", "10:00")])

    paris = available_slots(business=business(tz=PARIS, interval=60), **common)
    tunis = available_slots(business=business(tz=TUNIS, interval=60), **common)

    assert paris[0] == datetime(2026, 10, 6, 7, 0, tzinfo=UTC)
    assert tunis[0] == datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
    assert local_times(paris, PARIS) == local_times(tunis, TUNIS) == ["09:00"]


def test_every_returned_slot_is_timezone_aware_utc():
    """A naive datetime anywhere in this system is a bug waiting to happen."""
    slots = available_slots(
        business=business(),
        service=service(),
        on_date=TUESDAY,
        rules=[rule("09:00", "10:00")],
    )

    assert slots
    for slot in slots:
        assert slot.tzinfo is not None
        assert slot.utcoffset() == timedelta(0)


def test_daylight_saving_end_does_not_shift_opening_hours():
    """Paris goes UTC+2 -> UTC+1 on 25 October 2026.

    The shop opens at 09:00 local on both sides of the change. Because rules are stored
    as wall-clock time and converted per date, that happens with no intervention - the
    UTC instant differs, which is exactly right.
    """
    before = date(2026, 10, 20)  # Tuesday, still CEST (UTC+2)
    after = date(2026, 10, 27)  # Tuesday, now CET  (UTC+1)
    common = dict(
        business=business(interval=60), service=service(minutes=60), rules=[rule("09:00", "10:00")]
    )

    first = available_slots(on_date=before, **common)
    second = available_slots(on_date=after, **common)

    assert first[0] == datetime(2026, 10, 20, 7, 0, tzinfo=UTC)
    assert second[0] == datetime(2026, 10, 27, 8, 0, tzinfo=UTC)
    assert local_times(first) == local_times(second) == ["09:00"]


# --------------------------------------------------------------- now


def test_slots_already_past_are_not_offered():
    now = utc(PARIS, TUESDAY, "10:15")

    slots = available_slots(
        business=business(interval=30),
        service=service(minutes=30),
        on_date=TUESDAY,
        rules=[rule("09:00", "12:00")],
        now=now,
    )

    assert local_times(slots) == ["10:30", "11:00", "11:30"]


def test_a_past_date_offers_nothing():
    slots = available_slots(
        business=business(),
        service=service(),
        on_date=TUESDAY,
        rules=[rule("09:00", "17:00")],
        now=utc(PARIS, TUESDAY + timedelta(days=1), "09:00"),
    )

    assert slots == []


# ------------------------------------------------------- slot interval


@pytest.mark.parametrize(
    ("interval", "expected"),
    [
        (60, ["09:00", "10:00"]),
        (30, ["09:00", "09:30", "10:00"]),
        (15, ["09:00", "09:15", "09:30", "09:45", "10:00"]),
    ],
)
def test_slot_interval_controls_the_grid(interval, expected):
    slots = available_slots(
        business=business(interval=interval),
        service=service(minutes=60),
        on_date=TUESDAY,
        rules=[rule("09:00", "11:00")],
    )

    assert local_times(slots) == expected


def test_interval_of_one_minute_offers_every_minute():
    """The decision taken on 2026-09-16: no fixed grid."""
    slots = available_slots(
        business=business(interval=1),
        service=service(minutes=30),
        on_date=TUESDAY,
        rules=[rule("09:00", "10:00")],
    )

    assert len(slots) == 31  # 09:00 through 09:30 inclusive
    assert local_times(slots)[:3] == ["09:00", "09:01", "09:02"]
    assert local_times(slots)[-1] == "09:30"


def test_results_are_sorted_and_unique():
    slots = available_slots(
        business=business(interval=30),
        service=service(minutes=30),
        on_date=TUESDAY,
        rules=[rule("09:00", "11:00"), rule("10:00", "12:00")],  # deliberately overlapping
    )

    assert slots == sorted(slots)
    assert len(slots) == len(set(slots))
