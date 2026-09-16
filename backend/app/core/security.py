"""Password hashing and JSON Web Tokens.

Deliberately free of FastAPI and SQLAlchemy imports: these are pure functions over
strings, which makes them straightforward to test without a database or an HTTP client.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import settings

# Argon2id, the winner of the Password Hashing Competition and the current default
# recommendation. The library's defaults choose sensible memory and time costs.
#
# A hash is deliberately SLOW - a few hundred milliseconds. That is the whole point:
# a login costs one hash, but an attacker with a stolen database trying billions of
# guesses pays that cost every single time. Never hash passwords with SHA-256 or MD5;
# they are built to be fast, which is exactly wrong here.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Turn a plaintext password into a storable hash.

    The result embeds the algorithm, its parameters, and a random salt, so two users
    with the identical password still get completely different hashes. That salt is
    what stops an attacker precomputing one rainbow table against every account.
    """
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against a stored hash.

    Returns False rather than raising, so callers cannot accidentally leak *why* a
    login failed. "No such user" and "wrong password" must be indistinguishable to the
    outside world, or the error messages become an account-enumeration oracle.
    """
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError, ValueError):
        # VerificationError is the PARENT of VerifyMismatchError. Catching only the
        # child leaves a malformed-but-argon2-shaped hash raising out of here, which
        # would turn a login attempt into a 500 instead of a clean rejection.
        return False


def needs_rehash(password_hash: str) -> bool:
    """True if this hash used weaker parameters than we now use.

    Hardware gets faster, so recommended costs rise over time. On a successful login
    you can transparently re-hash the password with today's settings - the user never
    notices, and old accounts quietly get stronger.
    """
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, ValueError):
        return False


def create_access_token(
    subject: str | int,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Mint a signed token identifying one user.

    `subject` is the user id. The JWT spec calls this claim "sub", and it must be a
    string - PyJWT rejects an integer here, which is an easy hour to lose.

    Nothing secret goes in the payload: the payload is base64, not encryption, and
    anyone holding the token can read it. The id and role are fine; a password or an
    email would not be.
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))

    payload: dict[str, Any] = {
        "sub": str(subject),  # who this token is about
        "role": role,  # for the frontend to render with; the server re-checks the database
        "iat": now,  # issued at
        "exp": expire,  # expires at - PyJWT enforces this on decode
    }

    return jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Verify a token's signature and expiry, returning its claims.

    Returns None for anything untrustworthy - tampered, expired, signed with the wrong
    key, or malformed. Callers get one clear "no" instead of five exception types.

    `algorithms=` is pinned to what we configured, NOT read from the token's own header.
    Trusting the header lets an attacker present a token declaring `alg: none` and have
    it accepted unsigned.
    """
    try:
        return jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        return None
