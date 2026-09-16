"""Tests for password hashing and JWTs.

These are the functions an attacker probes first, so the tests assert security
properties, not just happy paths.
"""

import base64
import json
from datetime import timedelta

import jwt
import pytest

from app.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

PASSWORD = "correct horse battery staple"


# --------------------------------------------------------------- hashing


def test_hash_does_not_contain_the_password():
    """The stored value must not reveal what was typed."""
    assert PASSWORD not in hash_password(PASSWORD)


def test_same_password_hashes_differently_every_time():
    """Each hash gets a random salt.

    If identical passwords produced identical hashes, a leaked database would show at a
    glance which users share a password, and one rainbow table would crack them all.
    """
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_correct_password_verifies():
    assert verify_password(PASSWORD, hash_password(PASSWORD)) is True


def test_wrong_password_is_rejected():
    assert verify_password("not the password", hash_password(PASSWORD)) is False


@pytest.mark.parametrize(
    "bad_hash",
    ["", "not-a-hash", "$argon2id$v=19$garbage", "!seed-account-no-login!"],
    ids=["empty", "plain text", "malformed argon2", "seeded placeholder"],
)
def test_garbage_hashes_return_false_instead_of_raising(bad_hash):
    """A corrupt or placeholder hash must fail closed, not explode.

    The last case is what scripts/seed.py stores, which is how seeded accounts are
    guaranteed to be unable to log in.
    """
    assert verify_password(PASSWORD, bad_hash) is False


def test_empty_password_still_hashes_and_verifies():
    """Rejecting empty passwords is the API's job, not the hasher's."""
    hashed = hash_password("")
    assert verify_password("", hashed) is True
    assert verify_password("x", hashed) is False


# ------------------------------------------------------------------ JWT


def test_token_round_trip_carries_id_and_role():
    claims = decode_access_token(create_access_token(subject=42, role="owner"))

    assert claims is not None
    assert claims["sub"] == "42"  # the spec requires "sub" to be a string
    assert claims["role"] == "owner"


def test_expired_token_is_rejected():
    token = create_access_token(subject=1, role="customer", expires_delta=timedelta(seconds=-1))

    assert decode_access_token(token) is None


def test_tampered_payload_is_rejected():
    """Editing the payload breaks the signature.

    This is the property the whole scheme rests on: the payload is readable by anyone,
    but changing it invalidates the token.
    """
    token = create_access_token(subject=1, role="customer")
    header, payload, signature = token.split(".")

    decoded = json.loads(base64.urlsafe_b64decode(payload + "=="))
    assert decoded["role"] == "customer"  # readable without any secret - by design
    decoded["role"] = "owner"  # attempt a promotion

    forged_payload = base64.urlsafe_b64encode(json.dumps(decoded).encode()).decode().rstrip("=")

    assert decode_access_token(f"{header}.{forged_payload}.{signature}") is None


def test_token_signed_with_another_key_is_rejected():
    """Someone else's secret is not our secret."""
    foreign = jwt.encode({"sub": "1", "role": "owner"}, "a" * 48, algorithm="HS256")

    assert decode_access_token(foreign) is None


def test_unsigned_alg_none_token_is_rejected():
    """The classic JWT forgery: a token claiming it needs no signature.

    We are safe because decode_access_token pins `algorithms=[settings.jwt_algorithm]`
    rather than trusting the algorithm named in the token's own header.
    """

    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    forged = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': '1', 'role': 'owner'})}."

    assert decode_access_token(forged) is None


@pytest.mark.parametrize(
    "rubbish",
    ["", "not.a.token", "a.b.c", "onlyonepart"],
    ids=["empty", "three words", "invalid base64", "no dots"],
)
def test_malformed_tokens_are_rejected(rubbish):
    assert decode_access_token(rubbish) is None


def test_secret_key_is_not_printable():
    """SecretStr keeps the signing key out of logs and tracebacks."""
    assert "**" in str(settings.secret_key)
    assert settings.secret_key.get_secret_value() not in str(settings.secret_key)


# ------------------------------------------------------- settings


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        # What hosting providers actually hand you.
        ("postgresql://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        # Heroku's older scheme.
        ("postgres://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        # Already correct - must not be mangled into a double prefix.
        ("postgresql+psycopg://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        # A driver someone chose on purpose is left alone.
        ("postgresql+asyncpg://u:p@h:5432/d", "postgresql+asyncpg://u:p@h:5432/d"),
    ],
    ids=["plain", "heroku scheme", "already explicit", "other driver"],
)
def test_database_url_names_the_installed_driver(given, expected):
    """A bare postgresql:// means psycopg2 to SQLAlchemy, which we do not install.

    Getting this wrong produces `ModuleNotFoundError: No module named 'psycopg2'` at
    deploy time - an error that points nowhere near the actual cause.
    """
    from app.config import Settings

    assert Settings(database_url=given, secret_key="x" * 32).database_url == expected
