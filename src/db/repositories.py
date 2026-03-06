"""Data access layer — all database operations go through repositories."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    BackgroundJob,
    Issuer,
    MatchResult,
    Organization,
    Tender,
    TenderDocument,
    TenderLot,
)

logger = logging.getLogger(__name__)


class IssuerRepository:
    """Data access for issuers."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        name: str,
        org_identifier: str | None = None,
        **kwargs: str | None,
    ) -> Issuer:
        """Insert or update an issuer by org_identifier or name."""
        # Treat empty string as None to avoid unique constraint violations
        if not org_identifier:
            org_identifier = None

        existing: Issuer | None = None
        if org_identifier:
            result = await self.session.execute(
                select(Issuer).where(Issuer.org_identifier == org_identifier)
            )
            existing = result.scalar_one_or_none()

        if not existing:
            result = await self.session.execute(
                select(Issuer).where(Issuer.name == name)
            )
            existing = result.scalar_one_or_none()

        if existing:
            for k, v in kwargs.items():
                if v is not None and hasattr(existing, k):
                    setattr(existing, k, v)
            if org_identifier and not existing.org_identifier:
                existing.org_identifier = org_identifier
            return existing

        issuer = Issuer(name=name, org_identifier=org_identifier, **kwargs)
        self.session.add(issuer)
        await self.session.flush()
        return issuer


class TenderRepository:
    """Data access for tenders."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_from_raw(
        self,
        record: "RawTenderRecord",  # noqa: F821 — forward ref
        issuer: Issuer | None = None,
    ) -> Tender:
        """Insert or update a tender from a parsed record."""
        from src.ingestion.parser import RawTenderRecord

        source_id = f"{record.notice_id}-{record.notice_version}"

        result = await self.session.execute(
            select(Tender).where(Tender.source_id == source_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.title = record.title
            existing.contract_number = record.contract_number
            existing.description = record.description
            existing.cpv_codes = record.cpv_codes or []
            existing.estimated_value = record.estimated_value
            existing.currency = record.currency
            existing.publication_date = record.publication_date
            existing.submission_deadline = record.submission_deadline
            existing.execution_timeline = record.execution_timeline
            existing.execution_location = record.execution_location
            existing.nuts_codes = record.nuts_codes or []
            existing.contract_type = record.contract_type
            existing.eu_funded = record.eu_funded
            existing.renewable = record.renewable
            existing.lots_count = record.lots_count
            existing.max_lots_per_bidder = record.max_lots_per_bidder
            existing.platform_url = record.platform_url
            existing.document_portal_url = record.document_portal_url
            existing.raw_data = record.raw_data
            if issuer:
                existing.issuer_id = issuer.id
            tender = existing
        else:
            tender = Tender(
                source_id=source_id,
                title=record.title,
                contract_number=record.contract_number,
                cpv_codes=record.cpv_codes or [],
                estimated_value=record.estimated_value,
                currency=record.currency,
                publication_date=record.publication_date,
                submission_deadline=record.submission_deadline,
                execution_timeline=record.execution_timeline,
                execution_location=record.execution_location,
                nuts_codes=record.nuts_codes or [],
                contract_type=record.contract_type,
                eu_funded=record.eu_funded,
                renewable=record.renewable,
                lots_count=record.lots_count,
                max_lots_per_bidder=record.max_lots_per_bidder,
                platform_url=record.platform_url,
                document_portal_url=record.document_portal_url,
                raw_data=record.raw_data,
                issuer_id=issuer.id if issuer else None,
            )
            self.session.add(tender)

        await self.session.flush()

        # Upsert lots — delete existing and re-create
        if record.lots:
            await self.session.execute(
                delete(TenderLot).where(TenderLot.tender_id == tender.id)
            )
            for lot_rec in record.lots:
                lot = TenderLot(
                    tender_id=tender.id,
                    lot_number=lot_rec.lot_number,
                    title=lot_rec.title,
                    description=lot_rec.description,
                    estimated_value=lot_rec.estimated_value,
                    cpv_codes=lot_rec.cpv_codes or [],
                )
                self.session.add(lot)

        return tender

    async def find_by_id(self, tender_id: UUID) -> Tender | None:
        """Find a tender by ID, eager-loading issuer and lots."""
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(Tender)
            .where(Tender.id == tender_id)
            .options(
                selectinload(Tender.issuer),
                selectinload(Tender.lots),
                selectinload(Tender.documents),
            )
        )
        return result.scalar_one_or_none()

    async def count(self) -> int:
        """Count total tenders."""
        result = await self.session.execute(select(func.count(Tender.id)))
        return result.scalar_one()

    async def find_unenriched(self, limit: int = 100) -> list[Tender]:
        """Find tenders with no AI summary."""
        result = await self.session.execute(
            select(Tender)
            .where(Tender.ai_summary.is_(None))
            .where(Tender.title != "")
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_for_enrichment(self, limit: int = 100) -> list[Tender]:
        """Find all tenders with a title, regardless of enrichment status."""
        result = await self.session.execute(
            select(Tender)
            .where(Tender.title != "")
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_unembedded(self, limit: int = 100) -> list[Tender]:
        """Find tenders with searchable text but no embedding."""
        result = await self.session.execute(
            select(Tender)
            .where(Tender.embedding.is_(None))
            .where(Tender.ai_searchable_text.isnot(None))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_enrichment(
        self, tender_id: UUID, summary: str, searchable_text: str
    ) -> None:
        """Update AI-generated fields."""
        result = await self.session.execute(
            select(Tender).where(Tender.id == tender_id)
        )
        tender = result.scalar_one()
        tender.ai_summary = summary
        tender.ai_searchable_text = searchable_text

    async def update_embedding(
        self, tender_id: UUID, embedding: list[float]
    ) -> None:
        """Update the embedding vector."""
        await self.session.execute(
            text(
                "UPDATE tenders SET embedding = cast(:emb as vector) "
                "WHERE id = cast(:tid as uuid)"
            ).bindparams(tid=str(tender_id), emb=str(embedding))
        )

    async def search_by_vector(
        self,
        query_embedding: list[float],
        limit: int = 20,
    ) -> list[tuple[UUID, float]]:
        """Search tenders by cosine similarity using pgvector.

        Args:
            query_embedding: Query vector (384-dim).
            limit: Maximum results.

        Returns:
            List of (tender_id, similarity_score) sorted by descending similarity.
        """
        result = await self.session.execute(
            text(
                "SELECT t.id, 1 - (t.embedding <=> cast(:qvec as vector)) AS similarity "
                "FROM tenders t "
                "WHERE t.embedding IS NOT NULL "
                "ORDER BY t.embedding <=> cast(:qvec as vector) "
                "LIMIT :lim"
            ).bindparams(qvec=str(query_embedding), lim=limit)
        )
        return [(row.id, row.similarity) for row in result.fetchall()]


class OrganizationRepository:
    """Data access for organizations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self, tax_id: str, name: str, website: str | None = None
    ) -> tuple[Organization, bool]:
        """Insert or update an organization by tax_id.

        Returns:
            Tuple of (organization, is_new).
        """
        result = await self.session.execute(
            select(Organization).where(Organization.tax_id == tax_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = name
            if website is not None:
                existing.website = website
            return existing, False

        org = Organization(tax_id=tax_id, name=name, website=website)
        self.session.add(org)
        await self.session.flush()
        return org, True

    async def find_all(self) -> list[Organization]:
        """Return all organizations."""
        result = await self.session.execute(select(Organization))
        return list(result.scalars().all())

    async def find_by_id(self, org_id: UUID) -> Organization | None:
        """Find an organization by ID."""
        result = await self.session.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def count(self) -> int:
        """Count total organizations."""
        result = await self.session.execute(
            select(func.count(Organization.id))
        )
        return result.scalar_one()


class MatchResultRepository:
    """Data access for match results."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def delete_by_org(self, org_id: UUID) -> int:
        """Delete all match results for an organization. Returns count deleted."""
        result = await self.session.execute(
            delete(MatchResult).where(MatchResult.organization_id == org_id)
        )
        return result.rowcount  # type: ignore[return-value]

    async def save(
        self,
        org_id: UUID,
        tender_id: UUID,
        query_text: str,
        score: float,
    ) -> MatchResult:
        """Save a match result."""
        mr = MatchResult(
            organization_id=org_id,
            tender_id=tender_id,
            query_text=query_text,
            similarity_score=score,
        )
        self.session.add(mr)
        return mr

    async def find_by_org(self, org_id: UUID) -> list[MatchResult]:
        """Find all match results for an organization."""
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(MatchResult)
            .where(MatchResult.organization_id == org_id)
            .options(selectinload(MatchResult.tender))
            .order_by(MatchResult.similarity_score.desc())
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total match results."""
        result = await self.session.execute(
            select(func.count(MatchResult.id))
        )
        return result.scalar_one()


class BackgroundJobRepository:
    """Data access for background jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, job_type: str, params: dict) -> BackgroundJob:
        """Create a new background job with status=pending."""
        job = BackgroundJob(job_type=job_type, params=params, status="pending")
        self.session.add(job)
        await self.session.flush()
        return job

    async def find_by_id(self, job_id: UUID) -> BackgroundJob | None:
        """Find a background job by ID."""
        result = await self.session.execute(
            select(BackgroundJob).where(BackgroundJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self, job_id: UUID, status: str, **fields: object
    ) -> None:
        """Update job status and optional fields (pid, started_at, etc)."""
        values: dict[str, object] = {"status": status}
        values.update(fields)
        await self.session.execute(
            update(BackgroundJob)
            .where(BackgroundJob.id == job_id)
            .values(**values)
        )

    async def update_progress(
        self, job_id: UUID, current: int, total: int | None = None
    ) -> None:
        """Update progress counters."""
        values: dict[str, object] = {"progress_current": current}
        if total is not None:
            values["progress_total"] = total
        await self.session.execute(
            update(BackgroundJob)
            .where(BackgroundJob.id == job_id)
            .values(**values)
        )

    async def find_all(self, status_filter: str | None = None) -> list[BackgroundJob]:
        """List jobs, optionally filtered by status, newest first."""
        stmt = select(BackgroundJob).order_by(BackgroundJob.created_at.desc())
        if status_filter:
            stmt = stmt.where(BackgroundJob.status == status_filter)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_active(self) -> list[BackgroundJob]:
        """Find jobs with status pending or running."""
        result = await self.session.execute(
            select(BackgroundJob)
            .where(BackgroundJob.status.in_(["pending", "running"]))
            .order_by(BackgroundJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_by_status(self) -> dict[str, int]:
        """Return counts grouped by status."""
        result = await self.session.execute(
            select(BackgroundJob.status, func.count(BackgroundJob.id))
            .group_by(BackgroundJob.status)
        )
        return {row[0]: row[1] for row in result.fetchall()}
