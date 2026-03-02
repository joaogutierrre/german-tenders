"""AI enrichment pipeline — generate summary + searchable text for tenders."""

import logging
import time
from dataclasses import dataclass, field

from src.ai.llm_client import LLMError, OllamaClient
from src.ai.prompts import TENDER_SEARCHABLE, TENDER_SUMMARY
from src.config import settings
from src.db.repositories import TenderRepository
from src.db.session import get_session

logger = logging.getLogger(__name__)

MAX_SUMMARY_LEN = 300
MAX_SEARCHABLE_LEN = 3000


@dataclass
class EnrichmentResult:
    """Result of an enrichment batch run."""

    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


class EnrichmentPipeline:
    """Enrich tenders with AI-generated summary and searchable text."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    async def run(self, limit: int | None = None) -> EnrichmentResult:
        """Enrich a batch of unenriched tenders.

        Args:
            limit: Maximum tenders to process. Defaults to ingestion_batch_size.
        """
        batch_size = limit or settings.ingestion_batch_size
        start = time.time()
        result = EnrichmentResult()

        if not await self.client.is_available():
            logger.error("Ollama not available — skipping enrichment")
            return result

        async with get_session() as session:
            repo = TenderRepository(session)
            tenders = await repo.find_unenriched(limit=batch_size)

            if not tenders:
                logger.info("No unenriched tenders found")
                return result

            logger.info("Enriching %d tenders", len(tenders))

            for tender in tenders:
                result.processed += 1
                try:
                    summary = await self._generate_summary(tender)
                    searchable = await self._generate_searchable(tender)

                    # Truncate if needed
                    summary = summary[:MAX_SUMMARY_LEN]
                    searchable = searchable[:MAX_SEARCHABLE_LEN]

                    await repo.update_enrichment(
                        tender.id, summary=summary, searchable_text=searchable
                    )
                    # Commit after each tender so progress is resumable
                    await session.commit()
                    result.succeeded += 1
                    logger.info(
                        "Enriched tender %d/%d %s: %s",
                        result.processed,
                        len(tenders),
                        tender.id,
                        summary[:60],
                    )
                except LLMError as exc:
                    result.failed += 1
                    result.errors.append(f"{tender.id}: {exc}")
                    logger.warning("LLM error for tender %s: %s", tender.id, exc)
                except Exception as exc:
                    result.failed += 1
                    result.errors.append(f"{tender.id}: {exc}")
                    logger.error(
                        "Unexpected error enriching tender %s: %s",
                        tender.id,
                        exc,
                    )

        result.duration_seconds = time.time() - start
        return result

    async def _generate_summary(self, tender: "Tender") -> str:  # noqa: F821
        """Generate a short summary for a tender."""
        prompt = TENDER_SUMMARY.format(
            title=tender.title or "",
            description=(tender.raw_data or {}).get("description", "")
            if tender.raw_data
            else "",
            cpv_codes=", ".join(tender.cpv_codes or []),
            issuer_name="Unknown",
            deadline=tender.submission_deadline or "Not specified",
        )
        return await self.client.generate(prompt)

    async def _generate_searchable(self, tender: "Tender") -> str:  # noqa: F821
        """Generate rich searchable text for a tender."""
        prompt = TENDER_SEARCHABLE.format(
            title=tender.title or "",
            description=(tender.raw_data or {}).get("description", "")
            if tender.raw_data
            else "",
            cpv_codes=", ".join(tender.cpv_codes or []),
            contract_type=tender.contract_type or "Not specified",
            location=tender.execution_location or "Not specified",
            nuts_codes=", ".join(tender.nuts_codes or []),
        )
        return await self.client.generate(prompt)
