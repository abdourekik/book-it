"""TimeOff: specific closures that override the weekly pattern."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.business import Business


class TimeOff(Base):
    """A holiday, an appointment, a closed afternoon.

    Subtracted from the weekly availability when slots are calculated.
    """

    __tablename__ = "time_off"
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="end_after_start"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )

    # TIMESTAMPTZ here, unlike AvailabilityRule's TIME. "Closed on 24 December 2026" is
    # one specific stretch of history, not a repeating pattern - so it gets an absolute
    # moment, stored in UTC.
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    reason: Mapped[str | None] = mapped_column(String(200), default=None)

    business: Mapped[Business] = relationship(back_populates="time_off")

    def __repr__(self) -> str:
        return f"<TimeOff {self.starts_at} -> {self.ends_at} {self.reason!r}>"
