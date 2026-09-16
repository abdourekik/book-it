"""Working out which appointment times a customer can actually book.

The algorithm, in five steps:

    1. Take the weekly opening rules for the requested weekday and turn them into real
       UTC intervals for that specific date.
    2. Cut out any time off.
    3. Cut out any confirmed booking.
    4. Walk each remaining free interval in slot-interval steps, keeping every start
       where the whole service still fits before the interval ends.
    5. Drop anything already in the past.

Two conventions hold throughout, and most booking bugs come from breaking one of them:

* **Every datetime here is timezone-aware UTC.** Local wall-clock time appears only
  while converting an opening rule into an interval, and never leaves this module.
* **Every interval is half-open**, `[start, end)` - the start belongs to it, the end
  does not. That is what lets a 09:30-10:00 booking sit against a 10:00-10:30 one
  without them counting as overlapping.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models import AvailabilityRule, Booking, BookingStatus, Business, Service, TimeOff


@dataclass(frozen=True)
class Interval:
    """A half-open stretch of time in UTC: [start, end)."""

    start: datetime
    end: datetime

    @property
    def is_empty(self) -> bool:
        return self.start >= self.end

    def overlaps(self, other: Interval) -> bool:
        """True if the two share any real time.

        Touching endpoints do not count: [09:00, 10:00) and [10:00, 11:00) are
        adjacent, not overlapping.
        """
        return self.start < other.end and other.start < self.end

    def minus(self, other: Interval) -> list[Interval]:
        """This interval with `other` cut out of it.

        Returns zero, one, or two pieces:

            no overlap      -> [self]
            bite off an end -> one shorter interval
            covered whole   -> []
            bite the middle -> two intervals, one either side
        """
        if not self.overlaps(other):
            return [self]

        pieces = []
        if self.start < other.start:
            pieces.append(Interval(self.start, other.start))
        if other.end < self.end:
            pieces.append(Interval(other.end, self.end))
        return pieces


def _subtract_all(intervals: Iterable[Interval], blockers: Iterable[Interval]) -> list[Interval]:
    """Remove every blocker from every interval.

    Each blocker is applied to whatever is left after the previous one, so overlapping
    blockers are handled without any special case.
    """
    remaining = [i for i in intervals if not i.is_empty]

    for blocker in blockers:
        if blocker.is_empty:
            continue
        remaining = [piece for interval in remaining for piece in interval.minus(blocker)]

    return [i for i in remaining if not i.is_empty]


def _opening_intervals(
    business: Business, rules: Sequence[AvailabilityRule], on_date: date
) -> list[Interval]:
    """Turn the weekly rules into concrete UTC intervals for one date.

    This is where wall-clock time becomes an instant. "Tuesdays 09:00-17:00" is a
    pattern; on this particular Tuesday in this particular timezone it means one exact
    stretch of UTC.

    Daylight saving is handled by converting the two endpoints independently. On the day
    the clocks go back in Paris, 09:00-17:00 local is genuinely nine hours of real time,
    and this produces exactly that - without anyone writing a special case.
    """
    zone = ZoneInfo(business.timezone)
    weekday = on_date.weekday()  # 0 = Monday, matching AvailabilityRule.weekday

    intervals = []
    for rule in rules:
        if rule.weekday != weekday:
            continue

        start = datetime.combine(on_date, rule.start_time, tzinfo=zone).astimezone(UTC)
        end = datetime.combine(on_date, rule.end_time, tzinfo=zone).astimezone(UTC)

        interval = Interval(start, end)
        if not interval.is_empty:
            intervals.append(interval)

    return intervals


def _merge(intervals: Sequence[Interval]) -> list[Interval]:
    """Combine overlapping or touching intervals into the fewest possible.

    Two rules covering 09:00-11:00 and 10:00-12:00 describe one continuous stretch of
    opening hours, not two. Merging them first means the slot grid is laid out once
    across the whole stretch, so no slot is generated twice.
    """
    if not intervals:
        return []

    ordered = sorted(intervals, key=lambda i: i.start)
    merged = [ordered[0]]

    for current in ordered[1:]:
        last = merged[-1]
        if current.start <= last.end:  # overlapping or exactly touching
            merged[-1] = Interval(last.start, max(last.end, current.end))
        else:
            merged.append(current)

    return merged


def available_slots(
    *,
    business: Business,
    service: Service,
    on_date: date,
    rules: Sequence[AvailabilityRule],
    bookings: Sequence[Booking] = (),
    time_off: Sequence[TimeOff] = (),
    now: datetime | None = None,
) -> list[datetime]:
    """Every UTC instant at which this service can start on this date.

    Arguments are keyword-only: a call site that reads
    `available_slots(business, service, date, rules, bookings, time_off)` is one
    reordering away from a silent, hard-to-spot bug.

    `on_date` is a calendar date in the *business's* timezone - the day the customer
    tapped in the picker, not a UTC day.

    `now` is injectable so tests can pin "the present" instead of depending on the
    clock. Production leaves it out and gets the real time.

    The data is passed in rather than queried here, which keeps this function pure:
    no database, no network, no hidden state. Everything it does is determined by its
    arguments, so a failing test points at one thing.
    """
    if not service.is_active:
        return []

    now = now or datetime.now(UTC)
    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=max(1, business.slot_interval_minutes))

    open_intervals = _merge(_opening_intervals(business, rules, on_date))
    if not open_intervals:
        return []

    blockers = [Interval(off.starts_at, off.ends_at) for off in time_off] + [
        Interval(b.starts_at, b.ends_at)
        for b in bookings
        # Cancelled bookings must not block: freeing the slot is the entire point of
        # cancelling. This mirrors the `WHERE status = 'confirmed'` clause on the
        # database exclusion constraint, so the two agree about what "taken" means.
        if b.status == BookingStatus.CONFIRMED
    ]

    slots: list[datetime] = []
    for interval in _subtract_all(open_intervals, blockers):
        start = interval.start
        # `start + duration <= interval.end` is the rule that stops a 45-minute service
        # being offered at 17:30 when the shop closes at 18:00.
        while start + duration <= interval.end:
            if start >= now:  # never offer a time that has already passed
                slots.append(start)
            start += step

    return sorted(slots)
