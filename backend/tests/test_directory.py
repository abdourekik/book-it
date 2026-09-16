"""Tests for the public business directory."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models import Business, BusinessCategory, Service, User, UserRole

BROWSE = "/businesses"


def make_business(
    db,
    *,
    name: str,
    slug: str,
    category: BusinessCategory = BusinessCategory.BARBER,
    city: str | None = "Sfax",
    listed: bool = True,
    services: list[tuple[str, str]] | None = None,
    description: str | None = None,
) -> Business:
    """A business with an owner and, by default, one active service."""
    owner = User(
        email=f"{slug}@example.com",
        password_hash="x",
        full_name="Owner",
        role=UserRole.OWNER,
    )
    db.add(owner)
    db.flush()

    business = Business(
        owner_id=owner.id,
        name=name,
        slug=slug,
        timezone="Africa/Tunis",
        category=category,
        city=city,
        is_listed=listed,
        description=description,
    )
    db.add(business)
    db.flush()

    for service_name, price in services if services is not None else [("Haircut", "25.00")]:
        db.add(
            Service(
                business_id=business.id,
                name=service_name,
                duration_minutes=30,
                price=Decimal(price),
                currency="TND",
            )
        )

    db.commit()
    return business


@pytest.fixture
def directory(db):
    """A small directory: four businesses across three categories and two cities."""
    make_business(
        db,
        name="Ali Barbershop",
        slug="ali-barbers",
        category=BusinessCategory.BARBER,
        city="Sfax",
        services=[("Haircut", "25.00"), ("Beard trim", "12.00")],
        description="Classic cuts and hot-towel shaves.",
    )
    make_business(
        db,
        name="Zen Salon",
        slug="zen-salon",
        category=BusinessCategory.SALON,
        city="Sfax",
        services=[("Colour", "80.00")],
    )
    make_business(
        db,
        name="Nour Dental",
        slug="nour-dental",
        category=BusinessCategory.DENTIST,
        city="Tunis",
        services=[("Check-up", "60.00")],
    )
    make_business(
        db,
        name="Tunis Cuts",
        slug="tunis-cuts",
        category=BusinessCategory.BARBER,
        city="Tunis",
        services=[("Haircut", "30.00")],
    )
    return db


# ------------------------------------------------------------ listing


def test_browsing_returns_every_listed_business(client, directory):
    body = client.get(BROWSE).json()

    assert body["total"] == 4
    assert len(body["items"]) == 4


def test_results_are_ordered_by_name(client, directory):
    """Stable ordering, or page 2 can repeat a row from page 1."""
    names = [item["name"] for item in client.get(BROWSE).json()["items"]]

    assert names == sorted(names)


def test_a_card_carries_what_the_grid_needs(client, directory):
    card = next(i for i in client.get(BROWSE).json()["items"] if i["slug"] == "ali-barbers")

    assert card["category"] == "barber"
    assert card["city"] == "Sfax"
    assert card["service_count"] == 2
    assert card["from_price"] == "12.00"  # the CHEAPEST service, not the first
    assert card["currency"] == "TND"


def test_cards_do_not_carry_the_full_service_list(client, directory):
    """A 24-card page should not haul every service of every business."""
    card = client.get(BROWSE).json()["items"][0]

    assert "services" not in card


# ------------------------------------------------------- what is hidden


def test_unlisted_businesses_are_hidden(client, db, directory):
    make_business(db, name="Private Clinic", slug="private-clinic", listed=False)

    slugs = [i["slug"] for i in client.get(BROWSE).json()["items"]]

    assert "private-clinic" not in slugs


def test_an_unlisted_business_is_still_bookable_by_link(client, db, directory):
    """Opting out of the directory must not break the original private-link model."""
    make_business(db, name="Private Clinic", slug="private-clinic", listed=False)

    assert client.get("/businesses/private-clinic").status_code == 200


def test_businesses_with_no_services_are_hidden(client, db, directory):
    """A business with nothing bookable is a dead end for a customer."""
    make_business(db, name="Empty Shop", slug="empty-shop", services=[])

    slugs = [i["slug"] for i in client.get(BROWSE).json()["items"]]

    assert "empty-shop" not in slugs


def test_businesses_whose_services_are_all_retired_are_hidden(client, db, directory):
    business = make_business(db, name="Closed Down", slug="closed-down")
    for service in business.services:
        service.is_active = False
    db.commit()

    slugs = [i["slug"] for i in client.get(BROWSE).json()["items"]]

    assert "closed-down" not in slugs


# ------------------------------------------------------------ filtering


def test_filtering_by_category(client, directory):
    body = client.get(BROWSE, params={"category": "barber"}).json()

    assert body["total"] == 2
    assert {i["slug"] for i in body["items"]} == {"ali-barbers", "tunis-cuts"}


def test_filtering_by_city_ignores_case(client, directory):
    body = client.get(BROWSE, params={"city": "sfax"}).json()

    assert body["total"] == 2
    assert all(i["city"] == "Sfax" for i in body["items"])


def test_filters_combine(client, directory):
    body = client.get(BROWSE, params={"category": "barber", "city": "Tunis"}).json()

    assert [i["slug"] for i in body["items"]] == ["tunis-cuts"]


def test_search_matches_the_name(client, directory):
    body = client.get(BROWSE, params={"q": "barber"}).json()

    assert "ali-barbers" in {i["slug"] for i in body["items"]}


def test_search_matches_the_description(client, directory):
    body = client.get(BROWSE, params={"q": "hot-towel"}).json()

    assert [i["slug"] for i in body["items"]] == ["ali-barbers"]


def test_search_is_case_insensitive(client, directory):
    assert client.get(BROWSE, params={"q": "ZEN"}).json()["total"] == 1


def test_an_unknown_category_is_rejected_not_silently_empty(client, directory):
    """A typo in a shared link should be loud, not look like an empty city."""
    response = client.get(BROWSE, params={"category": "spaceship"})

    assert response.status_code == 422


def test_no_matches_is_an_empty_page_not_an_error(client, directory):
    body = client.get(BROWSE, params={"city": "Nowhere"}).json()

    assert body["total"] == 0
    assert body["items"] == []


# -------------------------------------------------------------- paging


def test_paging_returns_a_window_and_the_full_total(client, directory):
    body = client.get(BROWSE, params={"limit": 2, "offset": 0}).json()

    assert len(body["items"]) == 2
    assert body["total"] == 4  # the total ignores paging
    assert body["limit"] == 2
    assert body["offset"] == 0


def test_pages_do_not_overlap(client, directory):
    first = client.get(BROWSE, params={"limit": 2, "offset": 0}).json()["items"]
    second = client.get(BROWSE, params={"limit": 2, "offset": 2}).json()["items"]

    assert {i["slug"] for i in first}.isdisjoint({i["slug"] for i in second})


def test_a_limit_above_the_cap_is_rejected(client, directory):
    """Nobody gets to ask for the whole table in one request."""
    assert client.get(BROWSE, params={"limit": 5000}).status_code == 422


def test_a_negative_offset_is_rejected(client, directory):
    assert client.get(BROWSE, params={"offset": -1}).status_code == 422


# ---------------------------------------------------------- categories


def test_categories_are_returned_with_counts(client, directory):
    body = client.get("/businesses/categories").json()
    counts = {row["category"]: row["count"] for row in body}

    assert counts == {"barber": 2, "salon": 1, "dentist": 1}


def test_empty_categories_are_omitted(client, directory):
    """A chip reading "Fitness (0)" looks like a bug."""
    categories = {row["category"] for row in client.get("/businesses/categories").json()}

    assert "fitness" not in categories
    assert "tutor" not in categories


def test_categories_can_be_scoped_to_a_city(client, directory):
    body = client.get("/businesses/categories", params={"city": "Tunis"}).json()
    counts = {row["category"]: row["count"] for row in body}

    assert counts == {"barber": 1, "dentist": 1}


def test_the_categories_route_is_not_swallowed_by_the_slug_route(client, directory):
    """Route order matters: /businesses/{slug} would match "categories" otherwise."""
    response = client.get("/businesses/categories")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# -------------------------------------------------------------- cities


def test_cities_are_listed_alphabetically_without_duplicates(client, directory):
    assert client.get("/businesses/cities").json() == ["Sfax", "Tunis"]


def test_a_business_without_a_city_does_not_produce_a_null_entry(client, db, directory):
    make_business(db, name="Online Tutor", slug="online-tutor", city=None)

    assert None not in client.get("/businesses/cities").json()
