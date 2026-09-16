"""Request and response shapes for the owner-managed resources."""

from __future__ import annotations

import re
from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo, available_timezones

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_timezone(value: str) -> str:
    """Reject anything ZoneInfo cannot load.

    Checked here rather than trusted, because a bad timezone does not fail loudly - it
    fails at slot-calculation time, long after the owner typed it, and looks like a
    booking bug rather than a settings mistake. `available_timezones()` is consulted
    first so the error names the problem instead of raising a ZoneInfoNotFoundError.
    """
    if value not in available_timezones():
        raise ValueError(
            f"{value!r} is not a recognised IANA timezone. Examples: Europe/Paris, Africa/Tunis"
        )
    ZoneInfo(value)  # cheap, and proves the data files are actually present
    return value


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=2, max_length=120)
    timezone: str
    description: str | None = None
    slot_interval_minutes: int = Field(default=1, ge=1, le=240)

    @field_validator("slug")
    @classmethod
    def check_slug(cls, value: str) -> str:
        value = value.strip().lower()
        if not SLUG_PATTERN.match(value):
            raise ValueError(
                "slug must be lowercase letters, digits and single hyphens, e.g. joes-barbershop"
            )
        return value

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, value: str) -> str:
        return _validate_timezone(value)


class BusinessUpdate(BaseModel):
    """Every field optional: this is a PATCH, so absent means "leave it alone".

    Distinct from None, which for `description` means "clear it".
    """

    name: str | None = Field(default=None, min_length=1, max_length=120)
    timezone: str | None = None
    description: str | None = None
    slot_interval_minutes: int | None = Field(default=None, ge=1, le=240)

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, value: str | None) -> str | None:
        return None if value is None else _validate_timezone(value)


class BusinessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    timezone: str
    description: str | None
    slot_interval_minutes: int


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    duration_minutes: int = Field(ge=1, le=1440)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="EUR", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def upper(cls, value: str) -> str:
        return value.upper()


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    duration_minutes: int
    price: Decimal
    currency: str
    is_active: bool


class AvailabilityRuleIn(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0 = Monday ... 6 = Sunday")
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class WeeklyAvailability(BaseModel):
    """The whole week, replaced in one request.

    Not per-rule CRUD. An owner thinks "these are my hours", not "delete rule 7, update
    rule 9" - and sending the complete set makes the update atomic, so a half-applied
    schedule can never exist.
    """

    rules: list[AvailabilityRuleIn]


class AvailabilityRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    weekday: int
    start_time: time
    end_time: time


class TimeOffCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=200)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone offset")
        return value

    @model_validator(mode="after")
    def end_after_start(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class TimeOffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    starts_at: datetime
    ends_at: datetime
    reason: str | None
