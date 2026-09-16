"""Database engine, sessions, and the FastAPI dependency that hands them out."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# The engine owns the connection pool. One per application, created at import time:
# opening a TCP connection to PostgreSQL takes milliseconds, so we open a handful once
# and lend them out rather than reconnecting on every request.
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # DEBUG=true in .env prints every SQL statement - useful while learning
    pool_pre_ping=True,  # test a pooled connection before using it; survives database restarts
    # Without this, a database that is simply not there (Docker Desktop closed, wrong
    # port, VPN down) makes the app hang indefinitely instead of failing. Ten seconds
    # then a clear error beats an infinite wait with no explanation.
    connect_args={"connect_timeout": 10},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    # Keep attributes readable after commit(). Without this, touching booking.id after
    # committing triggers a surprise SELECT - and fails outright if the session is closed.
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Give this request its own database session, and always close it afterwards.

    This is a FastAPI *dependency*. An endpoint that writes `db: Session = Depends(get_db)`
    gets a session without ever constructing one, and tests can swap in a different
    session by overriding this single function.

    The `yield` is what makes the cleanup reliable: FastAPI runs everything up to the
    yield before the endpoint, hands over the session, then runs the `finally` block
    afterwards - even if the endpoint raised. Think of a coat check: you hand over the
    coat, they hand back a ticket, and the coat comes back whatever happens inside.

    Each request gets its own session because a session is a unit of work with its own
    transaction and identity map. Sharing one between concurrent requests would let two
    users' changes land in the same transaction.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# The dependency, packaged as a type. An endpoint writes `db: DbSession` and gets a
# session - shorter than repeating `Depends(get_db)` everywhere, and it avoids putting a
# function call in an argument default, which is a genuine Python trap: defaults are
# evaluated once at import time, not per call. FastAPI handles Depends() specially so
# the old style worked, but Annotated is the current idiom and reads better.
DbSession = Annotated[Session, Depends(get_db)]
