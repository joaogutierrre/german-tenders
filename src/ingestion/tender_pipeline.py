"""Orchestrates tender ingestion: fetch → parse → store."""

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


class TenderPipeline:
    """Orchestrates tender ingestion from API to database."""

    def __init__(self, api_client: TenderAPIClient | None = None) -> None:
        self.api_client = api_client or TenderAPIClient()

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
            except Exception:
                logger.error("Failed to process %s", current, exc_info=True)
                result.errors += 1

            current += timedelta(days=1)

        result.duration_seconds = time.time() - t0
        logger.info(
            "Pipeline complete: %d days, %d fetched, %d new, %d updated, %d errors (%.1fs)",
            result.days_processed,
            result.total_fetched,
            result.inserted,
            result.updated,
            result.errors,
            result.duration_seconds,
        )
        return result

    async def _process_day(self, pub_day: date) -> PipelineResult:
        """Fetch and store tenders for a single day."""
        result = PipelineResult()

        zip_bytes = await self.api_client.fetch_day_export(pub_day)
        if not zip_bytes:
            logger.info("No data for %s", pub_day)
            return result

        records = parse_csv_zip(zip_bytes)
        result.total_fetched = len(records)
        logger.info("Parsed %d records for %s", len(records), pub_day)

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
                    result.errors += 1

        return result
