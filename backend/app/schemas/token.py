"""The access token response."""

from pydantic import BaseModel


class Token(BaseModel):
    """What POST /auth/login returns.

    The field names are not ours to choose: `access_token` and `token_type` come from
    OAuth2 (RFC 6749). Following the standard means HTTP clients, Swagger UI's
    Authorize button, and most frontend libraries understand the response without any
    custom glue.
    """

    access_token: str
    token_type: str = "bearer"
