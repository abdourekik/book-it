"""Owner-facing management: the business, its services, its hours, its days off.

Every endpoint here is guarded by `CurrentOwner`, and every one of them reaches the
owner's business through `_my_business` rather than taking an id from the client. That
is deliberate: an endpoint that accepts `/businesses/{id}/services` has to remember to
check ownership, and one day it will not. Here there is nothing to forget - an owner can
only ever address their own business.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select

from app.api.deps import CurrentOwner
from app.db import DbSession
from app.models import (
    AvailabilityRule,
    Booking,
    BookingStatus,
    Business,
    Service,
    TimeOff,
    User,
)
from app.schemas.business import (
    AvailabilityRuleRead,
    BusinessCreate,
    BusinessRead,
    BusinessUpdate,
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
    TimeOffCreate,
    TimeOffRead,
    WeeklyAvailability,
)

router = APIRouter(prefix="/me", tags=["owner"])


def _my_business(db: DbSession, owner: User) -> Business:
    business = db.execute(
        select(Business).where(Business.owner_id == owner.id)
    ).scalar_one_or_none()

    if business is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "You have not set up a business yet - POST /me/business first",
        )
    return business


# ------------------------------------------------------------ business


@router.post(
    "/business",
    response_model=BusinessRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create my business",
)
def create_business(payload: BusinessCreate, db: DbSession, owner: CurrentOwner) -> Business:
    existing = db.execute(
        select(Business).where(Business.owner_id == owner.id)
    ).scalar_one_or_none()
    if existing is not None:
        # One business per owner - see decision 6 in docs/data-model.md.
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have a business")

    if db.execute(select(Business).where(Business.slug == payload.slug)).scalar_one_or_none():
        # Checked here so the owner gets a clear message naming the field, rather than
        # the raw unique-constraint error they would otherwise see.
        raise HTTPException(status.HTTP_409_CONFLICT, f"The slug {payload.slug!r} is taken")

    business = Business(owner_id=owner.id, **payload.model_dump())
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@router.get("/business", response_model=BusinessRead, summary="My business")
def read_business(db: DbSession, owner: CurrentOwner) -> Business:
    return _my_business(db, owner)


@router.patch("/business", response_model=BusinessRead, summary="Update my business")
def update_business(payload: BusinessUpdate, db: DbSession, owner: CurrentOwner) -> Business:
    business = _my_business(db, owner)

    # exclude_unset distinguishes "field absent" from "field set to null". Without it,
    # a PATCH that only changes the name would silently wipe the description.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(business, field, value)

    db.commit()
    db.refresh(business)
    return business


# ------------------------------------------------------------- services


@router.get("/services", response_model=list[ServiceRead], summary="My services")
def list_services(db: DbSession, owner: CurrentOwner) -> list[Service]:
    business = _my_business(db, owner)
    # Inactive ones included on purpose: the owner needs to see what they retired, and
    # be able to bring it back. The public booking page filters them out instead.
    return list(
        db.execute(
            select(Service).where(Service.business_id == business.id).order_by(Service.id)
        ).scalars()
    )


@router.post(
    "/services",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a service",
)
def create_service(payload: ServiceCreate, db: DbSession, owner: CurrentOwner) -> Service:
    business = _my_business(db, owner)

    service = Service(business_id=business.id, **payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def _my_service(db: DbSession, owner: User, service_id: int) -> Service:
    business = _my_business(db, owner)
    service = db.execute(
        select(Service).where(Service.id == service_id, Service.business_id == business.id)
    ).scalar_one_or_none()

    if service is None:
        # 404 whether it does not exist or belongs to someone else. Distinguishing them
        # would let an owner probe for other businesses' service ids.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    return service


@router.patch("/services/{service_id}", response_model=ServiceRead, summary="Update a service")
def update_service(
    service_id: int, payload: ServiceUpdate, db: DbSession, owner: CurrentOwner
) -> Service:
    service = _my_service(db, owner, service_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)

    db.commit()
    db.refresh(service)
    return service


@router.delete("/services/{service_id}", response_model=ServiceRead, summary="Retire a service")
def retire_service(service_id: int, db: DbSession, owner: CurrentOwner) -> Service:
    """Deactivate rather than delete.

    Bookings point at services. Deleting the row would either break existing
    appointments or erase them, so the service is hidden from the booking page while
    history stays readable. Reactivate with PATCH is_active=true.
    """
    service = _my_service(db, owner, service_id)
    service.is_active = False
    db.commit()
    db.refresh(service)
    return service


# --------------------------------------------------------- availability


@router.get("/availability", response_model=list[AvailabilityRuleRead], summary="My weekly hours")
def list_availability(db: DbSession, owner: CurrentOwner) -> list[AvailabilityRule]:
    business = _my_business(db, owner)
    return list(
        db.execute(
            select(AvailabilityRule)
            .where(AvailabilityRule.business_id == business.id)
            .order_by(AvailabilityRule.weekday, AvailabilityRule.start_time)
        ).scalars()
    )


@router.put(
    "/availability", response_model=list[AvailabilityRuleRead], summary="Replace my weekly hours"
)
def replace_availability(
    payload: WeeklyAvailability, db: DbSession, owner: CurrentOwner
) -> list[AvailabilityRule]:
    """Replace the entire weekly schedule in one transaction.

    Delete-then-insert inside a single commit, so the schedule is never half-applied: a
    crash between the two leaves the old hours intact rather than an empty week.

    Existing bookings are deliberately NOT checked. A booking made under the old hours
    stays valid - the owner committed to it - and narrowing the hours only stops *new*
    bookings being offered. Time off works differently, because it is an explicit
    statement of absence rather than a change to what is on offer.
    """
    business = _my_business(db, owner)

    db.execute(delete(AvailabilityRule).where(AvailabilityRule.business_id == business.id))

    rules = [
        AvailabilityRule(business_id=business.id, **rule.model_dump()) for rule in payload.rules
    ]
    db.add_all(rules)
    db.commit()

    return list_availability(db, owner)


# ------------------------------------------------------------- time off


@router.get("/time-off", response_model=list[TimeOffRead], summary="My time off")
def list_time_off(db: DbSession, owner: CurrentOwner) -> list[TimeOff]:
    business = _my_business(db, owner)
    return list(
        db.execute(
            select(TimeOff).where(TimeOff.business_id == business.id).order_by(TimeOff.starts_at)
        ).scalars()
    )


@router.post(
    "/time-off",
    response_model=TimeOffRead,
    status_code=status.HTTP_201_CREATED,
    summary="Block out time",
)
def create_time_off(payload: TimeOffCreate, db: DbSession, owner: CurrentOwner) -> TimeOff:
    """Mark a stretch of time as unavailable.

    Refused if confirmed bookings already fall inside it. Accepting it would leave the
    owner simultaneously committed to an appointment and marked absent - and the
    customer would find out by turning up to a closed door. Better to make the owner
    cancel those bookings first, which at least sends them a cancellation email.
    """
    business = _my_business(db, owner)

    clashes = list(
        db.execute(
            select(Booking).where(
                Booking.business_id == business.id,
                Booking.status == BookingStatus.CONFIRMED,
                Booking.starts_at < payload.ends_at,
                Booking.ends_at > payload.starts_at,
            )
        ).scalars()
    )
    if clashes:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{len(clashes)} confirmed booking(s) fall in that period - cancel them first",
        )

    time_off = TimeOff(business_id=business.id, **payload.model_dump())
    db.add(time_off)
    db.commit()
    db.refresh(time_off)
    return time_off


@router.delete(
    "/time-off/{time_off_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a block of time off",
)
def delete_time_off(time_off_id: int, db: DbSession, owner: CurrentOwner) -> None:
    business = _my_business(db, owner)

    time_off = db.execute(
        select(TimeOff).where(TimeOff.id == time_off_id, TimeOff.business_id == business.id)
    ).scalar_one_or_none()

    if time_off is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Time off not found")

    # A real delete, unlike services. Nothing points at a TimeOff row, so removing it
    # loses no history - it simply makes those hours bookable again.
    db.delete(time_off)
    db.commit()
