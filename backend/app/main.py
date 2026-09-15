"""FastAPI application entry point."""

from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Appointment booking for small businesses.",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness check.

    Deployment platforms (Render) and uptime monitors hit this endpoint to ask
    'are you alive?'. It must stay fast and must never require a login.
    """
    return {"status": "ok", "environment": settings.environment}
