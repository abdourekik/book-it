"""Shared test setup.

pytest automatically imports this file before running tests, and any function marked
with @pytest.fixture here is available to every test in this folder — no import needed.
That is the one piece of pytest magic worth knowing.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """A fake browser pointed at our API.

    TestClient calls the app directly in memory: no network, no running server, no
    `uvicorn` in another terminal. That is why the tests are fast and why CI can run
    them on a machine with nothing else started.

    Any test that declares an argument named `client` receives this automatically.
    """
    return TestClient(app)
