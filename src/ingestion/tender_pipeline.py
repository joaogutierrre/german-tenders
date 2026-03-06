"""Orchestrates tender ingestion: fetch → parse → store → enrich URLs."""

import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta

from src.db.repositories import IssuerRepository, TenderRepository
from src.db.session import get_session
from src.ingestion.api_client import TenderAPIClient
from src.ingestion.parser import parse_csv_zip

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Summary of an ingestion run."""

    days_processed: int = 0
    total_fetched: int = 0
    inserted: int = 0
    updated: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    ocds_urls_updated: int = 0
    exports_archived: int = 0


class TenderPipeline:
    """Orchestrates tender ingestion from API to database."""

    def __init__(
        self,
        api_client: TenderAPIClient | None = None,
        archive_exports: bool | None = None,
    ) -> None:
        self.api_client = api_client or TenderAPIClient()
        if archive_exports is None:
            from src.config import settings

            self._archive_exports = settings.archive_raw_exports
        else:
            self._archive_exports = archive_exports

    async def run(self, days: int = 7) -> PipelineResult:
        """Ingest tenders from the last N days.

        Processes one day at a time, committing after each day.
        """
        end = date.today() - timedelta(days=1)  # yesterday (data is delayed)
        start = end - timedelta(days=days - 1)
        return await self._run_range(start, end)

    async def run_date(self, target_date: date) -> PipelineResult:
        """Ingest tenders for a specific date."""
        return await self._run_range(target_date, target_date)

    async def _run_range(self, start: date, end: date) -> PipelineResult:
        """Process a date range, one day at a time."""
        result = PipelineResult()
        t0 = time.time()

        current = start
        while current <= end:
            try:
                day_result = await self._process_day(current)
                result.days_processed += 1
                result.total_fetched += day_result.total_fetched
                result.inserted += day_result.inserted
                result.updated += day_result.updated
                result.errors += day_result.errors
                result.ocds_urls_updated += day_result.ocds_urls_updated
                result.exports_archived += day_result.exports_archived
            except Exception:
                logger.error("Failed to process %s", current, exc_info=True)
                result.errors += 1

            current += timedelta(days=1)

        result.duration_seconds = time.time() - t0
        logger.info(
            "Pipeline complete: %d days, %d fetched, %d new, %d updated, "
            "%d OCDS URLs, %d errors (%.1fs)",
            result.days_processed,
            result.total_fetched,
            result.inserted,
            result.updated,
            result.ocds_urls_updated,
            result.errors,
            result.duration_seconds,
        )
        return result

    async def _process_day(self, pub_day: date) -> PipelineResult:
        """Fetch and store tenders for a single day."""
        result = PipelineResult()

        # ── Step 1: Fetch and parse CSV export ──
        zip_bytes = await self.api_client.fetch_day_export(pub_day)
        if not zip_bytes:
            logger.info("No data for %s", pub_day)
            return result

        # Archive the CSV export (best-effort)
        await self._try_archive(pub_day, "csv.zip", zip_bytes, result)

        records = parse_csv_zip(zip_bytes)
        result.total_fetched = len(records)
        logger.info("Parsed %d records for %s", len(records), pub_day)

        # ── Step 2: Upsert tenders from CSV ──
        async with get_session() as session:
            issuer_repo = IssuerRepository(session)
            tender_repo = TenderRepository(session)

            for record in records:
                try:
                    # Upsert issuer
                    issuer = None
                    if record.issuer_name:
                        issuer = await issuer_repo.upsert(
                            name=record.issuer_name,
                            org_identifier=record.issuer_org_identifier,
                            contact_email=record.issuer_email,
                            contact_phone=record.issuer_phone,
                            address=record.issuer_address,
                            nuts_code=record.issuer_nuts_code,
                        )

                    # Check if tender exists already
                    source_id = f"{record.notice_id}-{record.notice_version}"
                    from sqlalchemy import select
                    from src.db.models import Tender

                    existing = await session.execute(
                        select(Tender.id).where(Tender.source_id == source_id)
                    )
                    is_update = existing.scalar_one_or_none() is not None

                    # Upsert tender
                    await tender_repo.upsert_from_raw(record, issuer)

                    if is_update:
                        result.updated += 1
                    else:
                        result.inserted += 1

                except Exception:
                    logger.warning(
                        "Error processing notice %s",
                        record.notice_id,
                        exc_info=True,
                    )
                    await session.rollback()
                    result.errors += 1

        # ── Step 3: Enrich document URLs from OCDS ──
        await self._enrich_from_ocds(pub_day, result)

        return result

    async def _enrich_from_ocds(
        self, pub_day: date, result: PipelineResult
    ) -> None:
        """Fetch OCDS export and enrich tenders with document URLs.

        Best-effort — failures are logged but never break the pipeline.
        """
        try:
            ocds_bytes = await self.api_client.fetch_day_export(
                pub_day, fmt="ocds.zip"
            )
            if not ocds_bytes:
                logger.debug("No OCDS data for %s", pub_day)
                return

            # Archive the OCDS export
            await self._try_archive(pub_day, "ocds.zip", ocds_bytes, result)

            from src.ingestion.ocds_enricher import (
                enrich_document_urls,
                parse_ocds_zip,
            )

            ocds_data = parse_ocds_zip(ocds_bytes)
            if ocds_data:
                ocds_result = await enrich_document_urls(ocds_data)
                result.ocds_urls_updated = ocds_result.tenders_updated
                logger.info(
                    "OCDS enrichment for %s: %d URLs updated, %d not found",
                    pub_day,
                    ocds_result.tenders_updated,
                    ocds_result.tenders_not_found,
                )
        except Exception:
            logger.warning(
                "OCDS document URL enrichment failed for %s",
                pub_day,
                exc_info=True,
            )

    async def _try_archive(
        self,
        pub_day: date,
        fmt: str,
        data: bytes,
        result: PipelineResult,
    ) -> None:
        """Archive a raw export ZIP to MinIO (best-effort).

        Args:
            pub_day: Publication date.
            fmt: Export format (``csv.zip``, ``ocds.zip``).
            data: Raw ZIP bytes.
            result: Pipeline result to update archive count.
        """
        if not self._archive_exports:
            return

        try:
            from src.documents.export_archiver import ExportArchiver

            archiver = ExportArchiver()
            key = await archiver.archive(pub_day, fmt, data)
            if key:
                result.exports_archived += 1
                logger.info("Archived %s for %s", fmt, pub_day)
        except Exception:
            logger.warning(
                "Failed to archive %s for %s", fmt, pub_day, exc_info=True
            )
