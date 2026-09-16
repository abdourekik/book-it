"""The public directory query: which businesses a customer can browse, and in what order.

Kept out of the router so the filtering rules can be read - and tested - without the HTTP
layer in the way.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Business, BusinessCategory, Service

# Capped so nobody can ask for the entire table in one request. The frontend pages
# through instead.
MAX_LIMIT = 50
DEFAULT_LIMIT = 24


@dataclass(frozen=True)
class Card:
    name: str
    slug: str
    category: BusinessCategory
    city: str | None
    image_url: str | None
    description: str | None
    from_price: Decimal | None
    currency: str | None
    service_count: int


def _listed() -> Select:
    """Businesses a customer is allowed to discover.

    Two conditions, and the second is the one people forget:

      * `is_listed` - the owner opted in to the directory
      * at least one ACTIVE service - a business with nothing bookable is a dead end.
        The customer clicks through, finds an empty page, and leaves.
    """
    has_active_service = (
        select(1).where(Service.business_id == Business.id, Service.is_active.is_(True)).exists()
    )
    return select(Business).where(Business.is_listed.is_(True), has_active_service)


def _apply_filters(
    stmt: Select,
    *,
    q: str | None,
    category: BusinessCategory | None,
    city: str | None,
) -> Select:
    if category is not None:
        stmt = stmt.where(Business.category == category)

    if city:
        # Case-insensitive exact match: "sfax" and "Sfax" are the same place, but "Sfax"
        # and "Sfax Nord" are not, so this deliberately does not use LIKE.
        stmt = stmt.where(func.lower(Business.city) == city.strip().lower())

    if q:
        # ILIKE rather than full-text search. Full-text would need a tsvector column, an
        # index, and a language configuration - worth it at thousands of rows, overkill
        # here, and it would make "barb" stop matching "barbershop".
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(Business.name.ilike(pattern) | Business.description.ilike(pattern))

    return stmt


def count_businesses(
    db: Session,
    *,
    q: str | None = None,
    category: BusinessCategory | None = None,
    city: str | None = None,
) -> int:
    """How many businesses match, ignoring paging."""
    inner = _apply_filters(_listed(), q=q, category=category, city=city).subquery()
    return db.execute(select(func.count()).select_from(inner)).scalar_one()


def list_businesses(
    db: Session,
    *,
    q: str | None = None,
    category: BusinessCategory | None = None,
    city: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> list[Card]:
    """One page of directory results, cheapest service first shown as `from_price`."""
    stmt = _apply_filters(_listed(), q=q, category=category, city=city)

    # Ordered by name so paging is stable. Without an explicit order, PostgreSQL may
    # return rows in a different sequence between queries and page 2 could repeat a row
    # from page 1.
    stmt = stmt.order_by(Business.name).limit(min(limit, MAX_LIMIT)).offset(max(offset, 0))

    businesses = list(db.execute(stmt).scalars())
    if not businesses:
        return []

    # One aggregate query for every business on the page, rather than two queries per
    # business inside the loop - the N+1 that turns a 24-card page into 49 round trips.
    ids = [b.id for b in businesses]
    rows = db.execute(
        select(
            Service.business_id,
            func.min(Service.price).label("from_price"),
            func.min(Service.currency).label("currency"),
            func.count().label("service_count"),
        )
        .where(Service.business_id.in_(ids), Service.is_active.is_(True))
        .group_by(Service.business_id)
    ).all()
    by_business = {row.business_id: row for row in rows}

    cards = []
    for business in businesses:
        row = by_business.get(business.id)
        cards.append(
            Card(
                name=business.name,
                slug=business.slug,
                category=business.category,
                city=business.city,
                image_url=business.image_url,
                description=business.description,
                from_price=row.from_price if row else None,
                currency=row.currency if row else None,
                service_count=row.service_count if row else 0,
            )
        )
    return cards


def category_counts(db: Session, *, city: str | None = None) -> list[tuple[BusinessCategory, int]]:
    """Every category that actually has something in it, largest first.

    Categories with no businesses are omitted rather than returned as zero - a filter
    chip reading "Dentist (0)" looks like a bug to a customer.
    """
    inner = _apply_filters(_listed(), q=None, category=None, city=city).subquery()

    rows = db.execute(
        select(inner.c.category, func.count().label("n"))
        .group_by(inner.c.category)
        .order_by(func.count().desc(), inner.c.category)
    ).all()

    return [(BusinessCategory(row.category), row.n) for row in rows]


def cities(db: Session) -> list[str]:
    """Distinct cities that have at least one listed business, alphabetically."""
    inner = _apply_filters(_listed(), q=None, category=None, city=None).subquery()

    rows = db.execute(
        select(inner.c.city).where(inner.c.city.is_not(None)).distinct().order_by(inner.c.city)
    ).all()

    return [row.city for row in rows]
