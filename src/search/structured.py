"""Structured (SQL-based) search filters for tenders."""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import Select, select

from src.db.models import Tender


@dataclass
class SearchFilters:
    """Combinable structured filters for tender search."""

    cpv_codes: list[str] | None = None
    nuts_codes: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None
    date_from: date | None = None
    date_to: date | None = None
    deadline_after: datetime | None = None
    contract_type: str | None = None
    issuer_name: str | None = None
    keyword: str | None = None

    @property
    def has_filters(self) -> bool:
        """Check if any filter is active."""
        return any([
            self.cpv_codes,
            self.nuts_codes,
            self.min_value is not None,
            self.max_value is not None,
            self.date_from,
            self.date_to,
            self.deadline_after,
            self.contract_type,
            self.issuer_name,
            self.keyword,
        ])


def build_filter_query(filters: SearchFilters) -> Select:
    """Build a SQLAlchemy select with the given filters.

    All active filters are combined with AND.
    """
    stmt = select(Tender)

    if filters.cpv_codes:
        # PostgreSQL array overlap operator (&&)
        stmt = stmt.where(
            Tender.cpv_codes.op("&&")(filters.cpv_codes)
        )

    if filters.nuts_codes:
        stmt = stmt.where(
            Tender.nuts_codes.op("&&")(filters.nuts_codes)
        )

    if filters.min_value is not None:
        stmt = stmt.where(Tender.estimated_value >= filters.min_value)

    if filters.max_value is not None:
        stmt = stmt.where(Tender.estimated_value <= filters.max_value)

    if filters.date_from:
        stmt = stmt.where(Tender.publication_date >= filters.date_from)

    if filters.date_to:
        stmt = stmt.where(Tender.publication_date <= filters.date_to)

    if filters.deadline_after:
        stmt = stmt.where(Tender.submission_deadline >= filters.deadline_after)

    if filters.contract_type:
        stmt = stmt.where(Tender.contract_type == filters.contract_type)

    if filters.issuer_name:
        from src.db.models import Issuer

        stmt = stmt.join(Issuer, Tender.issuer_id == Issuer.id).where(
            Issuer.name.ilike(f"%{filters.issuer_name}%")
        )

    if filters.keyword:
        pattern = f"%{filters.keyword}%"
        stmt = stmt.where(
            Tender.title.ilike(pattern) | Tender.ai_searchable_text.ilike(pattern)
        )

    return stmt
