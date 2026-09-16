"""AvailabilityRule: the recurring weekly opening pattern."""

from __future__ import annotations

from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.business import Business


class AvailabilityRule(Base):
    """One block of opening hours on one weekday.

    A shop that closes for lunch has two rows for Tuesday - 09:00-12:00 and 14:00-18:00.
    That is exactly why this is a table rather than a pair of columns on Business.

    No timestamps mixin here: these rows are small, rewritten wholesale whenever the
    owner edits their hours, and nobody needs to know when a row was created.
    """

    __tablename__ = "availability_rules"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_in_range"),
        CheckConstraint("end_time > start_time", name="end_after_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )

    # 0 = Monday ... 6 = Sunday, matching Python's datetime.weekday().
    # Pick one convention and write it down: Postgres EXTRACT(DOW) uses 0 = Sunday, and
    # mixing the two shifts every schedule by a day.
    weekday: Mapped[int] = mapped_column()

    # TIME, not TIMESTAMPTZ. These are wall-clock times in the business's own timezone:
    # "we open at nine" is a recurring pattern, not a moment in history. Converting to
    # UTC at calculation time is what keeps the shop opening at 9am across daylight
    # saving changes. See docs/data-model.md, decision 1.
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)

    business: Mapped[Business] = relationship(back_populates="availability_rules")

    def __repr__(self) -> str:
        return f"<AvailabilityRule weekday={self.weekday} {self.start_time}-{self.end_time}>"
