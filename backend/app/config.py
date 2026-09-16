"""Application settings, loaded from environment variables.

Nothing in Book-it hardcodes a password, hostname, or port. Every value that could
differ between your laptop and production lives here, and is read from the environment
(in development, from a `.env` file). That is what lets the exact same code run against
Docker locally and Supabase in production.
"""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> backend/app -> backend
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Every setting the backend needs.

    A field with a default is optional. A field WITHOUT a default (like `database_url`)
    is required: if it is missing, the app refuses to start instead of booting in a
    half-configured state and failing later at a confusing moment.
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Book-it API"
    environment: str = "development"
    debug: bool = False

    # Required. Format: postgresql+psycopg://user:password@host:port/dbname
    database_url: str

    # --- Authentication -------------------------------------------------------
    # Required, with no default on purpose. A default secret is worse than no secret:
    # it ships to production unnoticed, and anyone who has read the source can mint a
    # token claiming to be any user. SecretStr keeps it from appearing in logs or
    # tracebacks - printing the settings object shows "**********".
    secret_key: SecretStr

    # Pinned server-side rather than read from the token. A token that declares its own
    # algorithm can declare "none", which is a classic forgery attack.
    jwt_algorithm: str = "HS256"

    # Short-lived on purpose: a JWT cannot be revoked, so a stolen one is valid until it
    # expires. Thirty minutes bounds the damage.
    access_token_expire_minutes: int = 30

    # --- Email ---------------------------------------------------------------
    # Optional. Without it the app logs emails instead of sending them, so the project
    # runs locally with no account anywhere and the test suite never touches a network.
    resend_api_key: SecretStr | None = None
    email_from: str = "Book-it <onboarding@resend.dev>"

    # Where the frontend lives. Used to build the links inside emails, so it must be the
    # public URL in production, not localhost.
    app_base_url: str = "http://localhost:3000"


# Created once, when the app starts, and imported everywhere else.
settings = Settings()
