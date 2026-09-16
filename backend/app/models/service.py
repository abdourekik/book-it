"""Service: something a customer can book, with a duration and a price."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.business import Business


class Service(Base, TimestampMixin):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="duration_positive"),
        CheckConstraint("price >= 0", name="price_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(120))

    # The number that turns opening hours into bookable slots.
    duration_minutes: Mapped[int] = mapped_column()

    # NUMERIC, never FLOAT. A float cannot hold 0.10 exactly, so money arithmetic
    # drifts. Numeric(10, 2) is exact: ten digits total, two after the decimal point.
    # In Python this arrives as decimal.Decimal, not float.
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    # ISO 4217 code: EUR, TND, USD. A bare number is not a price.
    currency: Mapped[str] = mapped_column(String(3), default="EUR")

    # Soft delete. Bookings point at services, so removing a row would either break
    # existing appointments or silently erase them. Setting this to False hides the
    # service from the booking page while history stays intact.
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")

    business: Mapped[Business] = relationship(back_populates="services")
    bookings: Mapped[list[Booking]] = relationship(back_populates="service")

    def __repr__(self) -> str:
        return f"<Service id={self.id} name={self.name!r} {self.duration_minutes}min>"
