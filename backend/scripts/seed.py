"""Fill the database with realistic sample data for local development.

    python -m scripts.seed            # seed an empty database
    python -m scripts.seed --reset    # delete everything first, then seed

Run from the backend/ folder with the virtual environment active.

Two businesses in two different timezones, on purpose: a bug that treats local time as
UTC looks perfectly fine when everything sits in one zone, and falls apart the moment a
second one appears.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import (
    AvailabilityRule,
    Booking,
    BookingStatus,
    Business,
    Service,
    TimeOff,
    User,
    UserRole,
)

# Seeded accounts must never be able to log in. A real hash would let anyone who read
# this file into the app; a value that cannot be produced by any hashing algorithm can
# never match a password check. Phase 3 replaces this with proper hashing.
UNUSABLE_PASSWORD = "!seed-account-no-login!"

MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY = range(6)


def local_to_utc(tz_name: str, day: date, at: time) -> datetime:
    """Convert a wall-clock time in a business's own timezone into UTC.

    This is the conversion the whole app depends on. An owner says "Tuesday at 09:00";
    that means 09:00 *where the shop is*, which is 08:00 UTC in Paris in winter and
    07:00 UTC in summer. ZoneInfo knows the daylight-saving rules, so attaching the zone
    and then calling .astimezone(UTC) always produces the right instant.

    Never do this by adding a fixed number of hours. Offsets change twice a year.
    """
    return datetime.combine(day, at, tzinfo=ZoneInfo(tz_name)).astimezone(UTC)


def next_weekday(weekday: int, *, weeks_ahead: int = 0) -> date:
    """The next date falling on `weekday` (0 = Monday), today excluded."""
    today = datetime.now(UTC).date()
    days = (weekday - today.weekday()) % 7 or 7
    return today + timedelta(days=days + 7 * weeks_ahead)


def wipe(session: Session) -> None:
    """Delete every row, children before parents so foreign keys stay satisfied."""
    for model in (Booking, TimeOff, AvailabilityRule, Service, Business, User):
        session.execute(delete(model))
    session.commit()


def weekly_hours(
    business: Business, weekdays: list[int], blocks: list[tuple[time, time]]
) -> list[AvailabilityRule]:
    """One AvailabilityRule per (weekday, block) pair.

    Two blocks on the same weekday is how a lunch break is expressed - the shop is open
    09:00-12:00 and 14:00-18:00, and simply has no rule covering 12:00-14:00.
    """
    return [
        AvailabilityRule(business=business, weekday=day, start_time=start, end_time=end)
        for day in weekdays
        for start, end in blocks
    ]


def seed(session: Session) -> None:
    # ---------------------------------------------------------------- users
    joe = User(
        email="joe@example.com",
        password_hash=UNUSABLE_PASSWORD,
        full_name="Joe Fontaine",
        role=UserRole.OWNER,
    )
    amira = User(
        email="amira@example.com",
        password_hash=UNUSABLE_PASSWORD,
        full_name="Amira Belhaj",
        role=UserRole.OWNER,
    )
    sam = User(
        email="sam@example.com",
        password_hash=UNUSABLE_PASSWORD,
        full_name="Sam Carter",
        role=UserRole.CUSTOMER,
    )
    session.add_all([joe, amira, sam])

    # ----------------------------------------------------------- businesses
    barber = Business(
        owner=joe,
        name="Joe's Barbershop",
        slug="joes-barbershop",
        timezone="Europe/Paris",
        description="Classic cuts and hot-towel shaves since 2019.",
        slot_interval_minutes=1,
    )
    clinic = Business(
        owner=amira,
        name="Sfax Dental Clinic",
        slug="sfax-dental",
        timezone="Africa/Tunis",
        description="General dentistry and hygiene appointments.",
        slot_interval_minutes=1,
    )
    session.add_all([barber, clinic])

    # -------------------------------------------------------------- services
    haircut = Service(business=barber, name="Haircut", duration_minutes=30, price=Decimal("25.00"))
    beard = Service(business=barber, name="Beard trim", duration_minutes=20, price=Decimal("12.50"))
    full = Service(
        business=barber, name="Haircut + beard", duration_minutes=45, price=Decimal("32.00")
    )

    checkup = Service(
        business=clinic,
        name="Check-up",
        duration_minutes=30,
        price=Decimal("60.00"),
        currency="TND",
    )
    cleaning = Service(
        business=clinic,
        name="Cleaning",
        duration_minutes=45,
        price=Decimal("90.00"),
        currency="TND",
    )
    filling = Service(
        business=clinic,
        name="Filling",
        duration_minutes=60,
        price=Decimal("150.00"),
        currency="TND",
        # Offered in the past, no longer bookable - but old bookings still reference it.
        # This is the soft delete from docs/data-model.md, decision 4.
        is_active=False,
    )
    session.add_all([haircut, beard, full, checkup, cleaning, filling])

    # ---------------------------------------------------------- availability
    # Barber: weekdays with a lunch break, plus a shorter Saturday.
    session.add_all(
        weekly_hours(
            barber,
            [MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY],
            [(time(9, 0), time(12, 0)), (time(14, 0), time(18, 0))],
        )
        + weekly_hours(barber, [SATURDAY], [(time(10, 0), time(16, 0))])
    )

    # Clinic: straight through Monday to Thursday, half-day Friday.
    session.add_all(
        weekly_hours(
            clinic,
            [MONDAY, TUESDAY, WEDNESDAY, THURSDAY],
            [(time(8, 0), time(16, 0))],
        )
        + weekly_hours(clinic, [FRIDAY], [(time(8, 0), time(12, 0))])
    )

    # ------------------------------------------------------------- time off
    # Joe takes a Friday off two weeks out. Stored as absolute UTC moments, converted
    # from his local midnight-to-midnight.
    friday_off = next_weekday(FRIDAY, weeks_ahead=1)
    session.add(
        TimeOff(
            business=barber,
            starts_at=local_to_utc(barber.timezone, friday_off, time(0, 0)),
            ends_at=local_to_utc(barber.timezone, friday_off + timedelta(days=1), time(0, 0)),
            reason="Family wedding",
        )
    )

    # -------------------------------------------------------------- bookings
    next_tuesday = next_weekday(TUESDAY)
    next_wednesday = next_weekday(WEDNESDAY)

    def slot(business: Business, day: date, at: time, service: Service) -> dict:
        starts = local_to_utc(business.timezone, day, at)
        return {
            "business": business,
            "service": service,
            "starts_at": starts,
            "ends_at": starts + timedelta(minutes=service.duration_minutes),
        }

    session.add_all(
        [
            # A registered customer. Local 10:00 in Paris.
            Booking(**slot(barber, next_tuesday, time(10, 0), haircut), customer=sam),
            # A guest - no account, just a name and an email. This is the shape the
            # guest-booking decision made possible.
            Booking(
                **slot(barber, next_tuesday, time(11, 0), beard),
                guest_name="Lea Moreau",
                guest_email="lea@example.com",
            ),
            # Cancelled: it deliberately overlaps the 10:00 haircut above. The exclusion
            # constraint allows this precisely because the status is not 'confirmed',
            # which is what lets a cancelled slot be rebooked.
            Booking(
                **slot(barber, next_tuesday, time(10, 15), full),
                guest_name="Tom Blanc",
                guest_email="tom@example.com",
                status=BookingStatus.CANCELLED,
            ),
            # Clinic, a different timezone entirely. Local 09:00 in Tunis.
            Booking(**slot(clinic, next_wednesday, time(9, 0), checkup), customer=sam),
            Booking(
                **slot(clinic, next_wednesday, time(10, 0), cleaning),
                guest_name="Karim Zouari",
                guest_email="karim@example.com",
            ),
        ]
    )

    # A finished appointment from last week, against the now-inactive service. Proves
    # history survives a service being retired.
    last_week = datetime.now(UTC).date() - timedelta(days=7)
    session.add(
        Booking(
            **slot(clinic, last_week, time(14, 0), filling),
            customer=sam,
            status=BookingStatus.COMPLETED,
        )
    )

    session.commit()


def summarise(session: Session) -> None:
    print("\nSeeded:")
    for model, label in (
        (User, "users"),
        (Business, "businesses"),
        (Service, "services"),
        (AvailabilityRule, "availability rules"),
        (TimeOff, "time off"),
        (Booking, "bookings"),
    ):
        count = len(session.execute(select(model)).scalars().all())
        print(f"  {count:>3}  {label}")

    print("\nUpcoming bookings, shown in both zones:")
    stmt = (
        select(Booking).where(Booking.status == BookingStatus.CONFIRMED).order_by(Booking.starts_at)
    )
    for b in session.execute(stmt).scalars():
        local = b.starts_at.astimezone(ZoneInfo(b.business.timezone))
        print(
            f"  {b.starts_at:%Y-%m-%d %H:%M} UTC"
            f"  =  {local:%H:%M} {b.business.timezone:<15}"
            f"  {b.service.name:<12} for {b.customer_display_name}"
        )

    print("\nNo seeded account can log in: password_hash is a value no hash can produce.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset", action="store_true", help="delete all existing rows before seeding"
    )
    args = parser.parse_args()

    # A seed script that can wipe a production database is a loaded gun on the table.
    if settings.environment.lower() not in {"development", "test", "local"}:
        print(f"Refusing to run: ENVIRONMENT is {settings.environment!r}, not development.")
        return 1

    with SessionLocal() as session:
        existing = session.execute(select(User)).first()
        if existing and not args.reset:
            print("Database already has data. Re-run with --reset to wipe and reseed.")
            return 1
        if args.reset:
            wipe(session)
            print("Existing rows deleted.")

        seed(session)
        summarise(session)

    return 0


if __name__ == "__main__":
    sys.exit(main())
