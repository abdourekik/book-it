"""Tests for the /health endpoint."""


def test_health(client):
    """The health check answers 200 with a status of "ok".

    Note what this function does NOT do: create a TestClient, start a server, or import
    anything. The `client` argument matches the name of the fixture in conftest.py, so
    pytest builds one and hands it over. That is the whole trick.
    """
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
