"""Dependencies that answer "who is calling?" and "are they allowed?".

FastAPI resolves these before the endpoint body runs, so an endpoint that declares
`user: CurrentOwner` can assume an authenticated owner is present. There is no way to
forget the check, because the check is in the signature.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db import DbSession
from app.models.user import User, UserRole

# Reads the `Authorization: Bearer <token>` header, and puts an Authorize button in
# /docs so the interactive documentation can call protected endpoints.
#
# auto_error=False so a missing header arrives here as None rather than FastAPI raising
# its own 403 first - this way every rejection goes through one place and returns a
# consistent 401 with the WWW-Authenticate header the HTTP spec asks for.
bearer_scheme = HTTPBearer(auto_error=False, description="Paste the token from /auth/login")

BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def _unauthorised() -> HTTPException:
    """401: we do not know who you are.

    Distinct from 403 below, and the distinction is not cosmetic. 401 means "your
    credentials are missing or invalid - try authenticating". 403 means "we know exactly
    who you are, and the answer is still no". A client can retry after a 401 by logging
    in again; retrying a 403 is pointless.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(credentials: BearerToken, db: DbSession) -> User:
    """Turn a bearer token into the User it refers to.

    Note that the user is loaded from the database rather than trusted from the token's
    claims. A token is a snapshot of who someone was when they logged in; by the time
    they use it, the account may have been deleted or had its role changed. Thirty
    minutes of stale authority is a long time in an application that manages other
    people's calendars.

    The cost is one indexed primary-key lookup per request, which is cheap. The `role`
    claim inside the token is still useful - to the *frontend*, which can render the
    owner dashboard without an extra round trip - but it is never what the server
    authorises against.
    """
    if credentials is None:
        raise _unauthorised()

    claims = decode_access_token(credentials.credentials)
    if claims is None:
        raise _unauthorised()

    subject = claims.get("sub")
    if subject is None:
        raise _unauthorised()

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        # A well-formed, correctly signed token whose "sub" is not a number should not
        # be possible - but a crash here would be a 500, so fail closed instead.
        raise _unauthorised() from None

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorised()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def optional_user(credentials: HTTPAuthorizationCredentials | None, db: Session) -> User | None:
    """The caller if they are signed in, or None if they are not.

    For endpoints open to both - booking works with an account or as a guest. A missing
    or invalid token means "treat this as a guest", not "reject the request", so this
    returns None where get_current_user would raise.

    A plain function rather than a dependency, because it is called from inside an
    endpoint that has already decided it needs both branches.
    """
    if credentials is None:
        return None

    claims = decode_access_token(credentials.credentials)
    if claims is None:
        return None

    subject = claims.get("sub")
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None

    return db.get(User, user_id)


def require_role(*allowed: UserRole):
    """Build a dependency that admits only the given roles.

    This is a *dependency factory*: calling it returns a function, and that function is
    what FastAPI runs. The factory exists so the allowed roles can differ per endpoint
    while the checking logic is written once.

        @router.get("/dashboard")
        def dashboard(user: Annotated[User, Depends(require_role(UserRole.OWNER))]):
            ...
    """

    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            names = " or ".join(role.value for role in allowed)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires the {names} role",
            )
        return user

    return dependency


# Ready-made aliases for the two roles, so endpoints read as plain English:
#   def my_services(user: CurrentOwner): ...
CurrentOwner = Annotated[User, Depends(require_role(UserRole.OWNER))]
CurrentCustomer = Annotated[User, Depends(require_role(UserRole.CUSTOMER))]
