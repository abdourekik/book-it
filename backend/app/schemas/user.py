"""Request and response shapes for users."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    """What a client sends to POST /auth/signup."""

    email: EmailStr
    # 8 is the floor, not an aspiration. Length beats complexity rules: a long
    # passphrase is both easier to remember and harder to crack than "P@ssw0rd!".
    # The 128 ceiling is a denial-of-service guard - argon2 is deliberately slow, so
    # hashing a multi-megabyte "password" would tie up a worker.
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    role: UserRole = UserRole.CUSTOMER

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        """Lowercase and trim, so Bob@X.com and bob@x.com cannot become two accounts.

        Doing this here means every entry point gets it - signup, login, and anything
        added later - rather than each endpoint remembering to.
        """
        return value.strip().lower()

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("full_name cannot be blank")
        return stripped


class UserLogin(BaseModel):
    """What a client sends to POST /auth/login."""

    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class UserRead(BaseModel):
    """What the API sends back about a user.

    Note what is absent: password_hash. A response schema is an allow-list, so a column
    added to the model tomorrow cannot leak into a JSON response by accident.
    """

    # Lets FastAPI build this straight from a SQLAlchemy object rather than a dict.
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    created_at: datetime
