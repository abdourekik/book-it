"""User: anyone with a login, either a business owner or a customer."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:  # imported only by type checkers, so there is no circular import
    from app.models.booking import Booking
    from app.models.business import Business


class UserRole(StrEnum):
    """What a user is allowed to be.

    StrEnum (Python 3.11+) means `UserRole.OWNER == "owner"` is True, which keeps JSON
    serialisation and comparisons painless. It replaces the older `class X(str, Enum)`
    trick, which ruff flags as UP042.
    """

    OWNER = "owner"
    CUSTOMER = "customer"


class User(Base, TimestampMixin):
    # "user" is a reserved word in PostgreSQL - `SELECT * FROM user` returns the current
    # database user, not your table. Plural table names sidestep that entirely, so every
    # table in this project is plural.
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Stored lowercased by the application layer, so Bob@x.com and bob@x.com cannot
    # become two accounts. The unique index also makes login lookups fast.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # A hash of the password, never the password. Phase 3 covers why, and which
    # algorithm. The column is wide enough for bcrypt or argon2 output.
    password_hash: Mapped[str] = mapped_column(String(255))

    full_name: Mapped[str] = mapped_column(String(120))

    role: Mapped[UserRole] = mapped_column(
        # values_callable makes PostgreSQL store "owner"/"customer" (the values) rather
        # than "OWNER"/"CUSTOMER" (the Python member names), which is SQLAlchemy's
        # default and a common surprise when you later read the table by hand.
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.CUSTOMER,
    )

    # One owner has at most one business (see decision 6 in docs/data-model.md).
    business: Mapped[Business | None] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

    # Bookings this user made as a customer. Guest bookings have no user at all.
    bookings: Mapped[list[Booking]] = relationship(back_populates="customer")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"
