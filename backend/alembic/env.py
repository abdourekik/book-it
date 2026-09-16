"""Alembic environment: how migrations find the database and the models.

Two things were changed from the file `alembic init` generates:

1. The database URL comes from app.config.settings, not from alembic.ini. One source of
   truth, and no password ever gets written into a committed file.
2. target_metadata points at our Base.metadata, which is what makes `--autogenerate`
   able to compare the models against the real database.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# Make `app` importable when alembic runs from the backend/ folder.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402  (must come after the sys.path change)
from app.models import Base  # noqa: E402  (imports every model, populating the metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The picture of what the database *should* look like. Alembic compares this against
# what the database actually looks like, and writes a migration for the difference.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it.

    `alembic upgrade head --sql` uses this. Useful when a production database is only
    reachable by a DBA who wants to read the SQL before applying it.
    """
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and run the migrations."""
    # create_engine directly rather than engine_from_config: the URL then never passes
    # through configparser, which would treat a `%` in a password as an escape character.
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Notice a column changing type (e.g. VARCHAR(120) -> VARCHAR(200)), which
            # autogenerate ignores by default.
            compare_type=True,
            # Notice a server_default being added, changed, or removed.
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
