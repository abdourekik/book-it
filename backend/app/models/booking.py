"""Booking: one appointment."""

from __future__ import annotations

import secrets
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    literal_column,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.service import Service
    from app.models.user import User


class BookingStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


def generate_access_token() -> str:
    """A secret, unguessable handle for one booking.

    `secrets` draws from the operating system's cryptographic random source. Never use
    `random` for this - it is a predictable pseudo-random generator, and someone who
    sees a few tokens could work out the rest and cancel strangers' appointments.
    """
    return secrets.token_urlsafe(32)


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="end_after_start"),
        # A booking belongs to a registered customer OR to a guest - never both, never
        # neither. Without this, a row with no customer at all is possible, and no
        # screen downstream would know whose appointment it is.
        CheckConstraint(
            "(customer_id IS NOT NULL AND guest_name IS NULL AND guest_email IS NULL)"
            " OR "
            "(customer_id IS NULL AND guest_name IS NOT NULL AND guest_email IS NOT NULL)",
            name="customer_xor_guest",
        ),
        # The constraint that actually prevents double-booking.
        #
        # Reads as: for the same business, no two CONFIRMED bookings may have
        # overlapping time ranges. `&&` is "overlaps"; tstzrange builds a range from the
        # two timestamps. The WHERE clause lets a cancelled booking stop blocking the
        # slot it used to hold.
        #
        # This is enforced by PostgreSQL itself, so two customers clicking in the same
        # millisecond cannot both win - regardless of what the Python code does. A
        # check-then-insert in the application has a gap between the check and the
        # insert, and that gap is exactly where double-bookings are born.
        #
        # Requires the btree_gist extension (created in the migration): plain GiST
        # indexes cannot handle the `business_id WITH =` equality part on its own.
        ExcludeConstraint(
            ("business_id", "="),
            (literal_column("tstzrange(starts_at, ends_at)"), "&&"),
            name="no_overlapping_bookings",
            using="gist",
            where=text("status = 'confirmed'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )

    # RESTRICT, not CASCADE: a service with bookings against it cannot be deleted at
    # all. Services are deactivated instead (Service.is_active), which keeps history
    # readable.
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"), index=True
    )

    # Nullable, because guest booking is allowed. RESTRICT rather than SET NULL: setting
    # it to NULL would leave a row with no customer and no guest details, violating the
    # customer_xor_guest constraint above. Deleting a user with bookings is a deliberate
    # problem to solve later (anonymise rather than delete).
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, default=None
    )

    guest_name: Mapped[str | None] = mapped_column(String(120), default=None)
    guest_email: Mapped[str | None] = mapped_column(String(255), default=None)

    # The secret in the cancellation link emailed to the customer. Holding this token is
    # what authorises cancelling or rescheduling this one booking - a capability URL.
    # Logged-in bookings get one too, so there is a single cancellation path.
    access_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=generate_access_token
    )

    # Absolute moments, stored in UTC. ends_at is stored rather than computed from the
    # service duration so that changing a service later cannot rewrite past bookings.
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    status: Mapped[BookingStatus] = mapped_column(
        Enum(
            BookingStatus,
            name="booking_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=BookingStatus.CONFIRMED,
        server_default=BookingStatus.CONFIRMED.value,
        index=True,
    )

    business: Mapped[Business] = relationship(back_populates="bookings")
    service: Mapped[Service] = relationship(back_populates="bookings")
    customer: Mapped[User | None] = relationship(back_populates="bookings")

    @property
    def customer_display_name(self) -> str:
        """Who this booking is for, whether they have an account or not."""
        return self.customer.full_name if self.customer_id else (self.guest_name or "Guest")

    @property
    def customer_email(self) -> str:
        """Where confirmation and reminder emails go."""
        return self.customer.email if self.customer_id else (self.guest_email or "")

    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} {self.starts_at} "
            f"status={self.status.value} for={self.customer_display_name!r}>"
        )
