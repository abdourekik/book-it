"""Tests for the owner management endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

PASSWORD = "a long enough password"
BUSINESS = {
    "name": "Joe's Barbershop",
    "slug": "joes-barbershop",
    "timezone": "Europe/Paris",
    "slot_interval_minutes": 30,
}


def account(client, email: str, role: str) -> dict[str, str]:
    client.post(
        "/auth/signup",
        json={"email": email, "password": PASSWORD, "full_name": "Test", "role": role},
    )
    token = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def owner(client):
    return account(client, "joe@example.com", "owner")


@pytest.fixture
def customer(client):
    return account(client, "sam@example.com", "customer")


@pytest.fixture
def owner_with_business(client, owner):
    client.post("/me/business", json=BUSINESS, headers=owner)
    return owner


# ------------------------------------------------------------ access


def test_customers_cannot_reach_owner_endpoints(client, customer):
    assert client.get("/me/business", headers=customer).status_code == 403
    assert client.post("/me/services", json={}, headers=customer).status_code == 403


def test_owner_endpoints_need_a_token(client):
    assert client.get("/me/business").status_code == 401


def test_an_owner_without_a_business_gets_a_helpful_404(client, owner):
    response = client.get("/me/business", headers=owner)

    assert response.status_code == 404
    assert "POST /me/business" in response.json()["detail"]


# ---------------------------------------------------------- business


def test_an_owner_can_create_a_business(client, owner):
    response = client.post("/me/business", json=BUSINESS, headers=owner)

    assert response.status_code == 201
    assert response.json()["slug"] == "joes-barbershop"


def test_a_second_business_is_refused(client, owner_with_business):
    second = {**BUSINESS, "slug": "another-shop"}

    response = client.post("/me/business", json=second, headers=owner_with_business)

    assert response.status_code == 409
    assert "already have" in response.json()["detail"]


def test_a_taken_slug_is_refused(client, owner_with_business):
    other = account(client, "amira@example.com", "owner")

    response = client.post("/me/business", json=BUSINESS, headers=other)

    assert response.status_code == 409
    assert "taken" in response.json()["detail"]


def test_an_invalid_timezone_is_rejected(client, owner):
    response = client.post(
        "/me/business", json={**BUSINESS, "timezone": "Mars/Olympus"}, headers=owner
    )

    assert response.status_code == 422
    assert "IANA" in str(response.json())


def test_an_invalid_slug_is_rejected(client, owner):
    response = client.post("/me/business", json={**BUSINESS, "slug": "Joe's Shop!"}, headers=owner)

    assert response.status_code == 422


def test_patching_one_field_leaves_the_others_alone(client, owner_with_business):
    """exclude_unset in action: absent must not mean null."""
    client.patch("/me/business", json={"description": "Since 2019"}, headers=owner_with_business)

    response = client.patch(
        "/me/business", json={"name": "Joe & Sons"}, headers=owner_with_business
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Joe & Sons"
    assert response.json()["description"] == "Since 2019"  # not wiped


# ----------------------------------------------------------- services


def test_services_can_be_added_and_listed(client, owner_with_business):
    created = client.post(
        "/me/services",
        json={"name": "Haircut", "duration_minutes": 30, "price": "25.00"},
        headers=owner_with_business,
    )

    assert created.status_code == 201
    assert created.json()["currency"] == "EUR"
    assert created.json()["is_active"] is True

    listed = client.get("/me/services", headers=owner_with_business)
    assert [s["name"] for s in listed.json()] == ["Haircut"]


def test_a_zero_minute_service_is_rejected(client, owner_with_business):
    response = client.post(
        "/me/services",
        json={"name": "Nothing", "duration_minutes": 0, "price": "5.00"},
        headers=owner_with_business,
    )

    assert response.status_code == 422


def test_a_negative_price_is_rejected(client, owner_with_business):
    response = client.post(
        "/me/services",
        json={"name": "Refund", "duration_minutes": 30, "price": "-5.00"},
        headers=owner_with_business,
    )

    assert response.status_code == 422


def test_deleting_a_service_deactivates_it_rather_than_removing_it(client, owner_with_business):
    service_id = client.post(
        "/me/services",
        json={"name": "Haircut", "duration_minutes": 30, "price": "25.00"},
        headers=owner_with_business,
    ).json()["id"]

    response = client.delete(f"/me/services/{service_id}", headers=owner_with_business)

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    # Still listed for the owner, so it can be brought back.
    assert len(client.get("/me/services", headers=owner_with_business).json()) == 1


def test_a_retired_service_can_be_reactivated(client, owner_with_business):
    service_id = client.post(
        "/me/services",
        json={"name": "Haircut", "duration_minutes": 30, "price": "25.00"},
        headers=owner_with_business,
    ).json()["id"]
    client.delete(f"/me/services/{service_id}", headers=owner_with_business)

    response = client.patch(
        f"/me/services/{service_id}", json={"is_active": True}, headers=owner_with_business
    )

    assert response.json()["is_active"] is True


def test_one_owner_cannot_touch_another_owners_service(client, owner_with_business):
    service_id = client.post(
        "/me/services",
        json={"name": "Haircut", "duration_minutes": 30, "price": "25.00"},
        headers=owner_with_business,
    ).json()["id"]

    intruder = account(client, "amira@example.com", "owner")
    client.post("/me/business", json={**BUSINESS, "slug": "other-shop"}, headers=intruder)

    response = client.patch(
        f"/me/services/{service_id}", json={"name": "Hijacked"}, headers=intruder
    )

    # 404, not 403 - telling them it exists but is not theirs would let them enumerate ids.
    assert response.status_code == 404


# ------------------------------------------------------- availability


def test_weekly_hours_can_be_set_and_read_back(client, owner_with_business):
    response = client.put(
        "/me/availability",
        json={
            "rules": [
                {"weekday": 1, "start_time": "09:00", "end_time": "12:00"},
                {"weekday": 1, "start_time": "14:00", "end_time": "18:00"},
            ]
        },
        headers=owner_with_business,
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert [r["start_time"] for r in response.json()] == ["09:00:00", "14:00:00"]


def test_putting_availability_replaces_rather_than_appends(client, owner_with_business):
    client.put(
        "/me/availability",
        json={"rules": [{"weekday": 1, "start_time": "09:00", "end_time": "17:00"}]},
        headers=owner_with_business,
    )

    response = client.put(
        "/me/availability",
        json={"rules": [{"weekday": 2, "start_time": "10:00", "end_time": "16:00"}]},
        headers=owner_with_business,
    )

    assert len(response.json()) == 1
    assert response.json()[0]["weekday"] == 2


def test_availability_can_be_cleared(client, owner_with_business):
    client.put(
        "/me/availability",
        json={"rules": [{"weekday": 1, "start_time": "09:00", "end_time": "17:00"}]},
        headers=owner_with_business,
    )

    assert (
        client.put("/me/availability", json={"rules": []}, headers=owner_with_business).json() == []
    )


def test_end_before_start_is_rejected(client, owner_with_business):
    response = client.put(
        "/me/availability",
        json={"rules": [{"weekday": 1, "start_time": "17:00", "end_time": "09:00"}]},
        headers=owner_with_business,
    )

    assert response.status_code == 422


def test_an_invalid_weekday_is_rejected(client, owner_with_business):
    response = client.put(
        "/me/availability",
        json={"rules": [{"weekday": 7, "start_time": "09:00", "end_time": "17:00"}]},
        headers=owner_with_business,
    )

    assert response.status_code == 422


# ---------------------------------------------------------- time off


def next_week(hour: int) -> str:
    day = datetime.now(UTC) + timedelta(days=8)
    return day.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


def test_time_off_can_be_added_and_removed(client, owner_with_business):
    created = client.post(
        "/me/time-off",
        json={"starts_at": next_week(0), "ends_at": next_week(23), "reason": "Wedding"},
        headers=owner_with_business,
    )

    assert created.status_code == 201
    assert created.json()["reason"] == "Wedding"

    time_off_id = created.json()["id"]
    assert (
        client.delete(f"/me/time-off/{time_off_id}", headers=owner_with_business).status_code == 204
    )
    assert client.get("/me/time-off", headers=owner_with_business).json() == []


def test_time_off_ending_before_it_starts_is_rejected(client, owner_with_business):
    response = client.post(
        "/me/time-off",
        json={"starts_at": next_week(18), "ends_at": next_week(9)},
        headers=owner_with_business,
    )

    assert response.status_code == 422


def test_naive_timestamps_are_rejected(client, owner_with_business):
    response = client.post(
        "/me/time-off",
        json={"starts_at": "2026-12-24T09:00:00", "ends_at": "2026-12-24T18:00:00"},
        headers=owner_with_business,
    )

    assert response.status_code == 422


def test_time_off_clashing_with_a_confirmed_booking_is_refused(client, owner_with_business):
    """The owner cannot be committed to an appointment and absent at the same time."""
    service_id = client.post(
        "/me/services",
        json={"name": "Haircut", "duration_minutes": 30, "price": "25.00"},
        headers=owner_with_business,
    ).json()["id"]

    # Open every day, so the booking below is certain to be offerable.
    client.put(
        "/me/availability",
        json={
            "rules": [{"weekday": d, "start_time": "00:00", "end_time": "23:59"} for d in range(7)]
        },
        headers=owner_with_business,
    )

    slots = client.get(
        f"/businesses/{BUSINESS['slug']}/slots",
        params={
            "service_id": service_id,
            "date": (datetime.now(UTC) + timedelta(days=8)).date().isoformat(),
        },
    ).json()["slots"]
    assert slots, "expected the shop to have free slots"

    booked = client.post(
        "/bookings",
        json={
            "business_slug": BUSINESS["slug"],
            "service_id": service_id,
            "starts_at": slots[20],
            "guest_name": "Lea",
            "guest_email": "lea@example.com",
        },
    )
    assert booked.status_code == 201

    response = client.post(
        "/me/time-off",
        json={"starts_at": next_week(0), "ends_at": next_week(23)},
        headers=owner_with_business,
    )

    assert response.status_code == 409
    assert "cancel them first" in response.json()["detail"]


def test_time_off_is_allowed_once_the_clashing_booking_is_cancelled(client, owner_with_business):
    service_id = client.post(
        "/me/services",
        json={"name": "Haircut", "duration_minutes": 30, "price": "25.00"},
        headers=owner_with_business,
    ).json()["id"]
    client.put(
        "/me/availability",
        json={
            "rules": [{"weekday": d, "start_time": "00:00", "end_time": "23:59"} for d in range(7)]
        },
        headers=owner_with_business,
    )
    slots = client.get(
        f"/businesses/{BUSINESS['slug']}/slots",
        params={
            "service_id": service_id,
            "date": (datetime.now(UTC) + timedelta(days=8)).date().isoformat(),
        },
    ).json()["slots"]
    token = client.post(
        "/bookings",
        json={
            "business_slug": BUSINESS["slug"],
            "service_id": service_id,
            "starts_at": slots[20],
            "guest_name": "Lea",
            "guest_email": "lea@example.com",
        },
    ).json()["access_token"]

    client.post(f"/bookings/{token}/cancel")

    response = client.post(
        "/me/time-off",
        json={"starts_at": next_week(0), "ends_at": next_week(23)},
        headers=owner_with_business,
    )

    assert response.status_code == 201
