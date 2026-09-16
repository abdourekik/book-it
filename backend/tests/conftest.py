"""Shared test setup.

pytest imports this automatically, and any @pytest.fixture defined here is available to
every test in this folder without an import.

The database strategy: one separate test database, built once per run by the real
Alembic migrations, and every individual test wrapped in a transaction that is rolled
back afterwards. Tests therefore see a clean database without paying to recreate it, and
they cannot leak state into each other no matter what order they run in.

Migrations rather than Base.metadata.create_all() on purpose. create_all builds tables
from the models, which would hide any drift between the models and the migrations -
tests would pass while production broke.
"""

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR, settings
from app.db import get_db
from app.main import app


def _test_database_url() -> str:
    """The development URL with `_test` appended to the database name."""
    url = make_url(settings.database_url)
    return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


def _create_test_database_if_missing(url: str) -> None:
    """CREATE DATABASE cannot run inside a transaction, hence AUTOCOMMIT."""
    target = make_url(url)
    admin_url = target.set(database="postgres")

    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": target.database},
        ).scalar()
        if not exists:
            # The database name comes from our own config, not from user input.
            conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine():
    """A migrated test database, created once for the whole test run."""
    url = _test_database_url()
    _create_test_database_if_missing(url)

    # alembic/env.py reads settings.database_url, so point it at the test database for
    # the duration of the upgrade, then put it back.
    original = settings.database_url
    settings.database_url = url
    try:
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        command.upgrade(config, "head")
    finally:
        settings.database_url = original

    test_engine = create_engine(url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine):
    """A session whose changes are thrown away when the test ends.

    The outer transaction is never committed. Anything the test writes - including
    anything the endpoint under test commits - lives inside it and disappears on
    rollback. That is why a test can create a user with a fixed email and the next test
    can create the same one again.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """A fake browser pointed at the API, wired to the test session.

    TestClient calls the app in memory - no network, no running uvicorn. The dependency
    override swaps get_db for the rolled-back session above, so requests made through
    this client touch the test database and nothing else.
    """

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
