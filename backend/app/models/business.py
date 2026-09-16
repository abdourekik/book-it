"""Business: one barbershop, clinic, or tutor."""

from __future__ import annotations

from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.availability_rule import AvailabilityRule
    from app.models.booking import Booking
    from app.models.service import Service
    from app.models.time_off import TimeOff
    from app.models.user import User


class Business(Base, TimestampMixin):
    __tablename__ = "businesses"
    __table_args__ = (
        CheckConstraint(
            "slot_interval_minutes BETWEEN 1 AND 240",
            name="slot_interval_sane",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # unique=True is decision 6: one business per owner, for now. Removing this
    # constraint later is a one-line migration; assuming it everywhere is not.
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    name: Mapped[str] = mapped_column(String(120))

    # The public URL segment: book-it.app/barber-joe
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    # An IANA timezone name such as "Europe/Paris" or "Africa/Tunis". This is the field
    # that makes availability rules mean anything: "Tuesdays 09:00" is 09:00 *here*.
    # Never store an offset like "+01:00" - offsets change twice a year with daylight
    # saving, whereas the zone name stays correct forever.
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")

    # How far apart offered start times are. 1 = every free minute (the decision taken
    # on 2026-09-16); raise to 15 or 30 for a conventional grid without touching code.
    slot_interval_minutes: Mapped[int] = mapped_column(default=1, server_default="1")

    description: Mapped[str | None] = mapped_column(Text, default=None)

    owner: Mapped[User] = relationship(back_populates="business")

    # delete-orphan: deleting a business takes its services, hours, and time off with
    # it. Those rows are meaningless on their own.
    services: Mapped[list[Service]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    availability_rules: Mapped[list[AvailabilityRule]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    time_off: Mapped[list[TimeOff]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    bookings: Mapped[list[Booking]] = relationship(back_populates="business")

    @property
    def tzinfo(self) -> ZoneInfo:
        """The timezone as an object, ready for .astimezone().

        Parsed on each access rather than cached: ZoneInfo keeps its own internal cache,
        so this is cheap, and a cached attribute would go stale if an owner corrected
        their timezone.
        """
        return ZoneInfo(self.timezone)

    def __repr__(self) -> str:
        return f"<Business id={self.id} slug={self.slug!r} tz={self.timezone}>"
