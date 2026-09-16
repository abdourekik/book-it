"""Tests for authentication and role dependencies."""

from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentCustomer, CurrentOwner, CurrentUser
from app.core.security import create_access_token
from app.main import app
from app.models.user import User

ME = "/auth/me"
OWNER_ONLY = "/_test/owner-only"
CUSTOMER_ONLY = "/_test/customer-only"
ANY_USER = "/_test/any-user"

# Routes that exist only to exercise the role dependencies. Phase 4 will have real
# owner-only endpoints; until then, inventing production routes just to test a
# dependency would be the tail wagging the dog.
_probe = APIRouter(include_in_schema=False)


@_probe.get(OWNER_ONLY)
def _owner_only(user: CurrentOwner):
    return {"id": user.id, "role": user.role.value}


@_probe.get(CUSTOMER_ONLY)
def _customer_only(user: CurrentCustomer):
    return {"id": user.id, "role": user.role.value}


@_probe.get(ANY_USER)
def _any_user(user: CurrentUser):
    return {"id": user.id, "role": user.role.value}


app.include_router(_probe)


def make_account(client, email: str, role: str = "customer") -> str:
    """Sign up, log in, and return the access token."""
    password = "a long enough password"
    client.post(
        "/auth/signup",
        json={"email": email, "password": password, "full_name": "Test User", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------- who am I?


def test_me_returns_the_authenticated_user(client):
    token = make_account(client, "sam@example.com")

    response = client.get(ME, headers=auth(token))

    assert response.status_code == 200
    assert response.json()["email"] == "sam@example.com"
    assert "password_hash" not in response.json()


def test_me_without_a_token_is_401(client):
    response = client.get(ME)

    assert response.status_code == 401
    # The HTTP spec requires this header on a 401 so clients know how to authenticate.
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_a_garbage_token_is_401(client):
    assert client.get(ME, headers=auth("not-a-real-token")).status_code == 401


def test_me_with_an_expired_token_is_401(client):
    make_account(client, "sam@example.com")
    expired = create_access_token(subject=1, role="customer", expires_delta=timedelta(seconds=-1))

    assert client.get(ME, headers=auth(expired)).status_code == 401


def test_me_with_a_token_signed_by_another_key_is_401(client):
    import jwt

    foreign = jwt.encode({"sub": "1", "role": "owner"}, "x" * 48, algorithm="HS256")

    assert client.get(ME, headers=auth(foreign)).status_code == 401


def test_token_for_a_deleted_user_is_401(client, db):
    """The database is the source of truth, not the token.

    A valid, unexpired, correctly signed token must stop working the moment the account
    behind it is gone - otherwise a deleted user keeps access until their token expires.
    """
    token = make_account(client, "sam@example.com")
    assert client.get(ME, headers=auth(token)).status_code == 200

    user = db.execute(select(User).where(User.email == "sam@example.com")).scalar_one()
    db.delete(user)
    db.commit()

    assert client.get(ME, headers=auth(token)).status_code == 401


def test_sub_that_is_not_a_number_is_401(client):
    """A signed token can still be nonsense. Fail closed, never 500."""
    token = create_access_token(subject="not-an-id", role="customer")

    assert client.get(ME, headers=auth(token)).status_code == 401


# ---------------------------------------------------------- role checks


def test_owner_can_reach_an_owner_route(client):
    token = make_account(client, "joe@example.com", role="owner")

    response = client.get(OWNER_ONLY, headers=auth(token))

    assert response.status_code == 200
    assert response.json()["role"] == "owner"


def test_customer_is_forbidden_from_an_owner_route(client):
    token = make_account(client, "sam@example.com", role="customer")

    response = client.get(OWNER_ONLY, headers=auth(token))

    # 403, not 401: we know exactly who this is, and the answer is still no. Logging in
    # again would not help, which is precisely what distinguishes it from a 401.
    assert response.status_code == 403
    assert "owner" in response.json()["detail"]


def test_owner_is_forbidden_from_a_customer_route(client):
    token = make_account(client, "joe@example.com", role="owner")

    assert client.get(CUSTOMER_ONLY, headers=auth(token)).status_code == 403


def test_both_roles_can_reach_an_unrestricted_route(client):
    owner = make_account(client, "joe@example.com", role="owner")
    customer = make_account(client, "sam@example.com", role="customer")

    assert client.get(ANY_USER, headers=auth(owner)).status_code == 200
    assert client.get(ANY_USER, headers=auth(customer)).status_code == 200


def test_role_routes_still_require_authentication(client):
    """A role check must not accidentally become a way in without a token."""
    assert client.get(OWNER_ONLY).status_code == 401
    assert client.get(CUSTOMER_ONLY).status_code == 401


def test_role_is_read_from_the_database_not_the_token(client, db):
    """Changing a role takes effect immediately, without waiting for token expiry.

    The token still says "customer", but the account is now an owner. If the server
    authorised from the claim, this would be a 403 for the next thirty minutes - and
    worse, a demoted owner would keep their powers for just as long.
    """
    token = make_account(client, "sam@example.com", role="customer")
    assert client.get(OWNER_ONLY, headers=auth(token)).status_code == 403

    user = db.execute(select(User).where(User.email == "sam@example.com")).scalar_one()
    user.role = "owner"
    db.commit()

    assert client.get(OWNER_ONLY, headers=auth(token)).status_code == 200
