"""Application settings, loaded from environment variables.

Nothing in Book-it hardcodes a password, hostname, or port. Every value that could
differ between your laptop and production lives here, and is read from the environment
(in development, from a `.env` file). That is what lets the exact same code run against
Docker locally and Supabase in production.
"""

from pathlib import Path

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


# Created once, when the app starts, and imported everywhere else.
settings = Settings()
