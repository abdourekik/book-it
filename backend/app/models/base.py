"""The declarative base every model inherits from, plus shared columns."""

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Without this, PostgreSQL invents names like "bookings_business_id_fkey" and SQLite
# invents different ones, so a migration that drops a constraint by name works on one
# machine and fails on another. Fixing the pattern up front makes every constraint name
# predictable and identical everywhere.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Every model inherits from this.

    SQLAlchemy collects each subclass into `Base.metadata`, which is the complete
    picture of what the database should look like. Alembic compares that picture
    against the real database to work out what a migration needs to change.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Adds created_at and updated_at to any model that inherits it.

    `server_default=func.now()` means PostgreSQL fills these in, not Python. That
    matters: the database has one clock, whereas app servers can disagree with each
    other by seconds, and rows inserted by a migration or by hand still get a value.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
