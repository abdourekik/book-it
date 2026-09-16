"""Send 24-hour reminders for upcoming appointments.

    python -m scripts.send_reminders            # send
    python -m scripts.send_reminders --dry-run  # list what would be sent

Designed to be run by a scheduler - a Render Cron Job hitting it hourly. Not an
in-process background scheduler, for three reasons:

  * a web process that sleeps until 3am is a web process that a platform may restart,
    losing the schedule silently
  * two web instances would each run the scheduler and send every reminder twice
  * a cron failure is visible in the platform's dashboard; a dead thread is not

Safe to run as often as you like. It only selects bookings whose reminder_sent_at is
NULL and stamps each one as it goes, so a schedule that fires twice, or a run that
overlaps the previous one, still emails each customer exactly once.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core import email
from app.db import SessionLocal
from app.models import Booking, BookingStatus

# Appointments starting inside this window get a reminder. It is wider than an hour so
# that one missed cron run does not silently skip a day of customers.
WINDOW_START = timedelta(hours=23)
WINDOW_END = timedelta(hours=25)


def due_reminders(session: Session, now: datetime) -> list[Booking]:
    return list(
        session.execute(
            select(Booking)
            .where(
                Booking.status == BookingStatus.CONFIRMED,
                Booking.reminder_sent_at.is_(None),
                Booking.starts_at >= now + WINDOW_START,
                Booking.starts_at < now + WINDOW_END,
            )
            .order_by(Booking.starts_at)
        ).scalars()
    )


def send_all(session: Session, *, dry_run: bool = False, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    due = due_reminders(session, now)

    for booking in due:
        business = booking.business
        local = booking.starts_at.astimezone(business.tzinfo)
        print(f"  {booking.customer_email:32} {local:%Y-%m-%d %H:%M} {business.name}")

        if dry_run:
            continue

        email.send(
            email.booking_reminder(
                to=booking.customer_email,
                customer_name=booking.customer_display_name,
                business_name=business.name,
                service_name=booking.service.name,
                starts_at=booking.starts_at,
                timezone=business.timezone,
                manage_url=(f"{settings.app_base_url.rstrip('/')}/bookings/{booking.access_token}"),
            )
        )

        # Stamped one at a time and committed per booking. If the process dies halfway,
        # the customers already emailed stay marked, so restarting does not email them
        # again - at the cost of one extra round trip each, which is the right trade for
        # a job that runs a handful of rows per hour.
        booking.reminder_sent_at = datetime.now(UTC)
        session.commit()

    return len(due)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="list without sending")
    args = parser.parse_args()

    with SessionLocal() as session:
        print(f"Reminders due ({email.get_sender().name} sender):")
        count = send_all(session, dry_run=args.dry_run)

    if count == 0:
        print("  none")
    print(f"{'Would send' if args.dry_run else 'Sent'}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
