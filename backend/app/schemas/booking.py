"""Request and response shapes for bookings and slots."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.booking import BookingStatus


class SlotList(BaseModel):
    """Available start times for one service on one local date."""

    business_slug: str
    service_id: int
    date: str
    timezone: str
    duration_minutes: int
    # Always UTC. The frontend converts for display - one rule, applied in one place.
    slots: list[datetime]


class BookingCreate(BaseModel):
    """What a client sends to POST /bookings.

    A guest supplies guest_name and guest_email. A logged-in customer supplies neither
    and sends a bearer token instead. Mirrors the customer_xor_guest database
    constraint, so a bad request is a clean 422 rather than a 500 from the database.
    """

    business_slug: str
    service_id: int
    starts_at: datetime
    guest_name: str | None = Field(default=None, max_length=120)
    guest_email: EmailStr | None = None

    @field_validator("starts_at")
    @classmethod
    def must_be_timezone_aware(cls, value: datetime) -> datetime:
        """Reject naive datetimes outright.

        "2026-10-06T10:00:00" with no offset is ambiguous - 10:00 where? Accepting it
        and guessing UTC is how appointments end up an hour out. The client must say
        what it means: "2026-10-06T10:00:00+02:00" or "...Z".
        """
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "starts_at must include a timezone offset, e.g. 2026-10-06T10:00:00+02:00"
            )
        return value

    @model_validator(mode="after")
    def guest_details_come_as_a_pair(self):
        if (self.guest_name is None) != (self.guest_email is None):
            raise ValueError("guest_name and guest_email must be provided together")
        return self


class BookingReschedule(BaseModel):
    starts_at: datetime

    @field_validator("starts_at")
    @classmethod
    def must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("starts_at must include a timezone offset")
        return value


class ServiceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    duration_minutes: int
    price: Decimal
    currency: str


class BusinessPublic(BaseModel):
    """What the public booking page needs to render.

    Deliberately narrow: no owner, no id, no internal fields. This is the one schema
    served to people who are not logged in, so it is the one most worth keeping tight.

    Defined after ServiceSummary on purpose - the reference then points backwards and
    needs no quoted forward declaration.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str
    slug: str
    timezone: str
    description: str | None
    slot_interval_minutes: int
    services: list[ServiceSummary]


class BookingRead(BaseModel):
    """What the API returns for a booking.

    access_token is included because the client needs it to cancel later - it is the
    only handle a guest has. It is returned to whoever just created the booking, and to
    whoever already knows it; it is never listed publicly.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    starts_at: datetime
    ends_at: datetime
    status: BookingStatus
    access_token: str
    service: ServiceSummary
    customer_name: str
    customer_email: str
