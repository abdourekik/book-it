"""All models, re-exported.

Importing every model here matters for two reasons:

1. SQLAlchemy resolves relationships by class name at first use. If Booking is never
   imported, `Mapped["Booking"]` on Business cannot be resolved and blows up at runtime.
2. Alembic autogenerate only sees tables registered on `Base.metadata`. A model nobody
   imported is invisible, and Alembic would cheerfully generate a migration that drops
   the table it does not know about.

So: every new model gets added here.
"""

from app.models.availability_rule import AvailabilityRule
from app.models.base import Base
from app.models.booking import Booking, BookingStatus
from app.models.business import Business
from app.models.service import Service
from app.models.time_off import TimeOff
from app.models.user import User, UserRole

__all__ = [
    "AvailabilityRule",
    "Base",
    "Booking",
    "BookingStatus",
    "Business",
    "Service",
    "TimeOff",
    "User",
    "UserRole",
]
