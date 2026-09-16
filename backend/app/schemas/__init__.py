"""Pydantic schemas: the shapes the API accepts and returns.

Models (app/models) describe what the DATABASE stores. Schemas describe what crosses the
HTTP boundary. Keeping them separate is what stops `password_hash` accidentally
appearing in a JSON response because someone added a column.
"""

from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserRead

__all__ = ["Token", "UserCreate", "UserLogin", "UserRead"]
