"""Signup and login."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.security import create_access_token, hash_password, verify_password
from app.db import DbSession
from app.models.user import User
from app.schemas import Token, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

# One message for every failed login, whatever actually went wrong. "No such email" and
# "wrong password" must be indistinguishable: if they differ, anyone can feed the
# endpoint a list of addresses and learn which ones have accounts here. For a booking
# app that is a real privacy leak - it reveals who is a customer of which business.
INVALID_CREDENTIALS = "Incorrect email or password"


@router.post(
    "/signup",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
def signup(payload: UserCreate, db: DbSession) -> User:
    """Register a new user.

    FastAPI has already validated the body against UserCreate before this function
    runs: a malformed email or a six-character password never reaches here, and the
    client gets a 422 describing exactly which field was wrong.
    """
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        # Signup is the one place where revealing that an account exists is unavoidable
        # - the user has to be told why they cannot proceed. Rate limiting is the
        # mitigation here, not vagueness. (Not yet implemented; see PROGRESS.md.)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token, summary="Exchange credentials for a token")
def login(payload: UserLogin, db: DbSession) -> Token:
    """Verify an email and password, and return an access token."""
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()

    # Hash a throwaway value when the user does not exist, so a missing account takes
    # roughly as long as a wrong password. Without this, response times alone reveal
    # which emails are registered - a timing side channel.
    if user is None:
        verify_password(payload.password, "$argon2id$v=19$m=65536,t=3,p=4$invalid")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=create_access_token(subject=user.id, role=user.role.value))
