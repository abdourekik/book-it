"""Booking: create, view, cancel, reschedule. Plus the public slot listing."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError

from app import queries
from app.api.deps import BearerToken, CurrentUser, optional_user
from app.config import settings
from app.core import email
from app.db import DbSession
from app.domain.availability import available_slots
from app.models import Booking, BookingStatus, Business, Service
from app.schemas.booking import (
    BookingCreate,
    BookingRead,
    BookingReschedule,
    BusinessPublic,
    SlotList,
)

router = APIRouter(tags=["bookings"])

# The name of the PostgreSQL exclusion constraint from the initial migration. Matching
# on it lets us tell "that slot was just taken" apart from any other integrity error,
# so a genuine bug still surfaces as a 500 instead of being mislabelled a conflict.
OVERLAP_CONSTRAINT = "no_overlapping_bookings"

# PostgreSQL SQLSTATE codes that mean "another transaction beat you to it", rather than
# "your data is wrong".
#
# 40P01 deadlock_detected      - two transactions each waited on the other; one is shot
# 40001 serialization_failure  - the transaction could not be serialised safely
#
# These matter more than they look. When several transactions insert rows that conflict
# under an exclusion constraint, each one waits to learn whether the others commit. With
# enough of them the waits form a cycle, and PostgreSQL resolves it by aborting some -
# so the losers surface as OperationalError, NOT as the IntegrityError you would expect
# from a constraint violation. Catching only IntegrityError turns those into 500s.
TRANSIENT_CONFLICT_CODES = {"40P01", "40001"}


def _conflict_reason(exc: DBAPIError) -> str | None:
    """Return a human explanation if this error means "someone else got the slot"."""
    if isinstance(exc, IntegrityError) and OVERLAP_CONSTRAINT in str(exc.orig):
        return "That time was just taken - please pick another"

    if getattr(exc.orig, "sqlstate", None) in TRANSIENT_CONFLICT_CODES:
        # Our transaction was rolled back in a pile-up. The slot may or may not have
        # gone to someone else, so the honest answer is "try again".
        return "That time is being booked by someone else - please try again"

    return None


def _load_business_and_service(
    db: DbSession, slug: str, service_id: int
) -> tuple[Business, Service]:
    business = queries.get_business_by_slug(db, slug)
    if business is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Business not found")

    service = queries.get_service(db, business.id, service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")

    return business, service


def _slots_for(
    db: DbSession, business: Business, service: Service, on_date: date
) -> list[datetime]:
    """Fetch what the pure slot function needs, then call it."""
    start, end = queries.local_day_bounds(business.timezone, on_date)

    return available_slots(
        business=business,
        service=service,
        on_date=on_date,
        rules=queries.availability_rules(db, business.id),
        bookings=queries.bookings_overlapping(db, business.id, start, end),
        time_off=queries.time_off_overlapping(db, business.id, start, end),
    )


def manage_url(booking: Booking) -> str:
    """The capability URL emailed to the customer."""
    return f"{settings.app_base_url.rstrip('/')}/bookings/{booking.access_token}"


def _as_read(booking: Booking) -> dict:
    """Flatten a Booking into the response shape.

    customer_name and customer_email come from the model's properties, which already
    know whether this is a guest or a registered customer.
    """
    return {
        "id": booking.id,
        "starts_at": booking.starts_at,
        "ends_at": booking.ends_at,
        "status": booking.status,
        "access_token": booking.access_token,
        "service": booking.service,
        "customer_name": booking.customer_display_name,
        "customer_email": booking.customer_email,
    }


@router.get(
    "/businesses/{slug}",
    response_model=BusinessPublic,
    summary="A business and the services it offers",
)
def get_business(slug: str, db: DbSession) -> BusinessPublic:
    """Public - this is the page a customer lands on from a shared link."""
    business = queries.get_business_by_slug(db, slug)
    if business is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Business not found")

    return BusinessPublic(
        name=business.name,
        slug=business.slug,
        timezone=business.timezone,
        description=business.description,
        slot_interval_minutes=business.slot_interval_minutes,
        # Retired services are filtered out here. The owner still sees them in
        # /me/services so they can bring one back; a customer never should.
        services=[s for s in business.services if s.is_active],
    )


@router.get(
    "/businesses/{slug}/slots",
    response_model=SlotList,
    summary="Available start times for a service on a date",
)
def list_slots(
    slug: str,
    db: DbSession,
    service_id: Annotated[int, Query(description="Which service to book")],
    on: Annotated[date, Query(alias="date", description="Local calendar date, YYYY-MM-DD")],
) -> SlotList:
    """Public - no login needed to see when a business is free."""
    business, service = _load_business_and_service(db, slug, service_id)

    return SlotList(
        business_slug=business.slug,
        service_id=service.id,
        date=on.isoformat(),
        timezone=business.timezone,
        duration_minutes=service.duration_minutes,
        slots=_slots_for(db, business, service, on),
    )


@router.post(
    "/bookings",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Book an appointment",
)
def create_booking(
    payload: BookingCreate,
    db: DbSession,
    credentials: BearerToken,
    background: BackgroundTasks,
) -> dict:
    """Create a booking, for a logged-in customer or a guest.

    Two layers guard the slot, and they do different jobs:

      1. The availability check below produces a friendly 409 and is also what catches
         "you asked for 03:00 on a Sunday".
      2. The database exclusion constraint is what makes it TRUE. Between the check and
         the insert there is a gap, and under real concurrency two requests can both
         pass step 1. Only the constraint can reject one of them.

    Remove step 1 and the app still cannot double-book; it just returns an uglier
    error. Remove step 2 and it double-books under load, no matter how careful the
    Python is.
    """
    user = optional_user(credentials, db)

    if user is None and payload.guest_name is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Provide guest_name and guest_email, or sign in first",
        )
    if user is not None and payload.guest_name is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A signed-in customer must not send guest details",
        )

    business, service = _load_business_and_service(db, payload.business_slug, payload.service_id)

    if not service.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "That service is no longer offered")

    starts_at = payload.starts_at.astimezone(UTC)
    if starts_at < datetime.now(UTC):
        raise HTTPException(status.HTTP_409_CONFLICT, "That time is in the past")

    # The requested date as the BUSINESS sees it, which is the day whose opening hours
    # apply - not the UTC date, and not the customer's date.
    local_date = starts_at.astimezone(business.tzinfo).date()
    if starts_at not in _slots_for(db, business, service, local_date):
        raise HTTPException(status.HTTP_409_CONFLICT, "That time is not available")

    booking = Booking(
        business_id=business.id,
        service_id=service.id,
        customer_id=user.id if user else None,
        guest_name=payload.guest_name,
        guest_email=payload.guest_email,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=service.duration_minutes),
    )
    db.add(booking)

    try:
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        # Someone else committed the same slot between our check and our insert - or we
        # lost a deadlock trying. Either way the answer to the customer is the same.
        reason = _conflict_reason(exc)
        if reason is None:
            raise
        raise HTTPException(status.HTTP_409_CONFLICT, reason) from exc

    db.refresh(booking)

    # Queued, not awaited. FastAPI runs background tasks AFTER the response is sent, so
    # a slow email provider cannot make the customer wait - and cannot fail a booking
    # that is already committed.
    background.add_task(
        email.send,
        email.booking_confirmation(
            to=booking.customer_email,
            customer_name=booking.customer_display_name,
            business_name=business.name,
            service_name=service.name,
            starts_at=booking.starts_at,
            timezone=business.timezone,
            manage_url=manage_url(booking),
        ),
    )

    return _as_read(booking)


def _booking_or_404(db: DbSession, token: str) -> Booking:
    """Find a booking by its secret token.

    The token IS the authorisation - a capability URL. Anyone holding it may act on
    this one booking and nothing else, which is how a guest with no account cancels.
    A wrong token is a 404 rather than a 403: confirming that a token exists but is not
    yours would be an oracle for guessing them.
    """
    booking = queries.get_booking_by_token(db, token)
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return booking


@router.get("/bookings/{token}", response_model=BookingRead, summary="View a booking")
def get_booking(token: str, db: DbSession) -> dict:
    return _as_read(_booking_or_404(db, token))


@router.post("/bookings/{token}/cancel", response_model=BookingRead, summary="Cancel a booking")
def cancel_booking(token: str, db: DbSession, background: BackgroundTasks) -> dict:
    booking = _booking_or_404(db, token)

    if booking.status == BookingStatus.CANCELLED:
        # Already done. Returning 200 rather than an error makes the operation
        # idempotent: clicking the emailed link twice is harmless.
        return _as_read(booking)

    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"A {booking.status.value} booking cannot be cancelled"
        )

    # The row is kept, not deleted. The owner's cancellation-rate statistic needs it,
    # and the exclusion constraint ignores non-confirmed rows, so the slot frees up.
    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)

    background.add_task(
        email.send,
        email.booking_cancellation(
            to=booking.customer_email,
            customer_name=booking.customer_display_name,
            business_name=booking.business.name,
            service_name=booking.service.name,
            starts_at=booking.starts_at,
            timezone=booking.business.timezone,
            booking_url=manage_url(booking),
        ),
    )

    return _as_read(booking)


@router.post("/bookings/{token}/reschedule", response_model=BookingRead, summary="Move a booking")
def reschedule_booking(token: str, payload: BookingReschedule, db: DbSession) -> dict:
    """Move a confirmed booking to a new time.

    The booking's own span is excluded from the availability check, so moving 10:00 to
    10:15 is not blocked by the booking that is being moved.
    """
    booking = _booking_or_404(db, token)

    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"A {booking.status.value} booking cannot be moved"
        )

    business = booking.business
    service = booking.service
    starts_at = payload.starts_at.astimezone(UTC)

    if starts_at < datetime.now(UTC):
        raise HTTPException(status.HTTP_409_CONFLICT, "That time is in the past")

    local_date = starts_at.astimezone(business.tzinfo).date()
    start, end = queries.local_day_bounds(business.timezone, local_date)
    others = [
        b for b in queries.bookings_overlapping(db, business.id, start, end) if b.id != booking.id
    ]

    allowed = available_slots(
        business=business,
        service=service,
        on_date=local_date,
        rules=queries.availability_rules(db, business.id),
        bookings=others,
        time_off=queries.time_off_overlapping(db, business.id, start, end),
    )
    if starts_at not in allowed:
        raise HTTPException(status.HTTP_409_CONFLICT, "That time is not available")

    booking.starts_at = starts_at
    booking.ends_at = starts_at + timedelta(minutes=service.duration_minutes)

    try:
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        reason = _conflict_reason(exc)
        if reason is None:
            raise
        raise HTTPException(status.HTTP_409_CONFLICT, reason) from exc

    db.refresh(booking)
    return _as_read(booking)


@router.get(
    "/my/bookings",
    response_model=list[BookingRead],
    summary="My bookings (signed-in customers)",
)
def my_bookings(db: DbSession, user: CurrentUser) -> list[dict]:
    """Every booking this customer made, soonest first.

    Guest bookings cannot appear here - they have no customer_id, which is the trade
    that came with allowing booking without an account. A guest's only handle is the
    link they were emailed.
    """
    bookings = db.execute(
        select(Booking).where(Booking.customer_id == user.id).order_by(Booking.starts_at.desc())
    ).scalars()

    return [_as_read(b) for b in bookings]
