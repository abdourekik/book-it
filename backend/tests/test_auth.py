"""Tests for signup and login."""

from sqlalchemy import select

from app.core.security import decode_access_token
from app.models.user import User

SIGNUP = "/auth/signup"
LOGIN = "/auth/login"

ACCOUNT = {
    "email": "sam@example.com",
    "password": "a long enough password",
    "full_name": "Sam Carter",
}


def register(client, **overrides):
    return client.post(SIGNUP, json={**ACCOUNT, **overrides})


# --------------------------------------------------------------- signup


def test_signup_creates_a_user(client):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "sam@example.com"
    assert body["full_name"] == "Sam Carter"
    assert body["role"] == "customer"  # the default
    assert body["id"] > 0


def test_signup_response_never_contains_the_password(client):
    """UserRead is an allow-list, so secrets cannot leak by accident."""
    body = register(client).json()

    assert "password" not in body
    assert "password_hash" not in body
    assert ACCOUNT["password"] not in str(body)


def test_password_is_stored_hashed_not_plaintext(client, db):
    register(client)

    user = db.execute(select(User).where(User.email == ACCOUNT["email"])).scalar_one()

    assert user.password_hash != ACCOUNT["password"]
    assert user.password_hash.startswith("$argon2")


def test_signup_normalises_the_email(client, db):
    """BOB@Example.COM and bob@example.com are the same person."""
    response = register(client, email="  SAM@Example.COM  ")

    assert response.status_code == 201
    assert response.json()["email"] == "sam@example.com"
    assert db.execute(select(User).where(User.email == "sam@example.com")).scalar_one()


def test_duplicate_email_is_rejected(client):
    register(client)
    response = register(client, full_name="Someone Else")

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_duplicate_detection_ignores_case(client):
    register(client)
    response = register(client, email="SAM@EXAMPLE.COM")

    assert response.status_code == 409


def test_signup_can_create_an_owner(client):
    response = register(client, role="owner")

    assert response.status_code == 201
    assert response.json()["role"] == "owner"


def test_short_password_is_rejected(client):
    response = register(client, password="short")

    assert response.status_code == 422  # FastAPI validates before our code runs


def test_invalid_email_is_rejected(client):
    response = register(client, email="not-an-email")

    assert response.status_code == 422


def test_blank_name_is_rejected(client):
    response = register(client, full_name="   ")

    assert response.status_code == 422


# ---------------------------------------------------------------- login


def test_login_returns_a_usable_token(client):
    register(client)

    response = client.post(LOGIN, json={"email": ACCOUNT["email"], "password": ACCOUNT["password"]})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    claims = decode_access_token(body["access_token"])
    assert claims is not None
    assert claims["role"] == "customer"
    assert claims["sub"].isdigit()


def test_login_with_wrong_password_is_rejected(client):
    register(client)

    response = client.post(LOGIN, json={"email": ACCOUNT["email"], "password": "wrong password"})

    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_login_with_unknown_email_is_rejected(client):
    response = client.post(LOGIN, json={"email": "nobody@example.com", "password": "whatever123"})

    assert response.status_code == 401


def test_wrong_password_and_unknown_email_are_indistinguishable(client):
    """The security property that stops account enumeration.

    If these two responses differed, anyone could feed the endpoint a list of email
    addresses and learn which ones have accounts here - which, for a booking app,
    reveals who is a customer of which business.
    """
    register(client)

    wrong_password = client.post(
        LOGIN, json={"email": ACCOUNT["email"], "password": "wrong password"}
    )
    unknown_email = client.post(
        LOGIN, json={"email": "nobody@example.com", "password": "wrong password"}
    )

    assert wrong_password.status_code == unknown_email.status_code
    assert wrong_password.json() == unknown_email.json()


def test_login_email_is_case_insensitive(client):
    register(client)

    response = client.post(
        LOGIN, json={"email": "SAM@EXAMPLE.COM", "password": ACCOUNT["password"]}
    )

    assert response.status_code == 200


def test_seeded_accounts_cannot_log_in(client, db):
    """scripts/seed.py stores a hash no algorithm can produce."""
    db.add(
        User(
            email="seeded@example.com",
            password_hash="!seed-account-no-login!",
            full_name="Seeded User",
        )
    )
    db.commit()

    response = client.post(
        LOGIN, json={"email": "seeded@example.com", "password": "!seed-account-no-login!"}
    )

    assert response.status_code == 401
