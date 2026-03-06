"""AI enrichment pipeline — generate summary + searchable text for tenders."""

import asyncio
import inspect
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from src.ai.llm_client import LLMError, OllamaClient
from src.ai.prompts import TENDER_SEARCHABLE, TENDER_SUMMARY
from src.config import settings
from src.db.repositories import TenderRepository
from src.db.session import get_session

logger = logging.getLogger(__name__)

MAX_SUMMARY_LEN = 300
MAX_SEARCHABLE_LEN = 3000
GPU_CONCURRENCY = 10


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

    def __init__(
        self,
        client: OllamaClient | None = None,
        gpu: bool = False,
        state_file: Path | None = None,
    ) -> None:
        self.client = client or OllamaClient(model=settings.ollama_model_fast)
        self.gpu = gpu
        self.concurrency = GPU_CONCURRENCY if gpu else 1
        self.state_file = state_file
        self._tender_states: dict[str, dict] = {}
        self._state_lock = asyncio.Lock()

    def _write_state(self) -> None:
        """Persist per-tender states to the state file (JSON)."""
        if not self.state_file:
            return
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(
                json.dumps(self._tender_states, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            logger.debug("Failed to write state file", exc_info=True)

    def _set_tender_state(
        self, tender_id: str, status: str, title: str = "", error: str = ""
    ) -> None:
        """Update a tender's state and persist."""
        self._tender_states[tender_id] = {
            "status": status,
            "title": title[:80],
            "error": error[:200] if error else "",
            "updated_at": time.time(),
        }
        self._write_state()

    async def run(
        self,
        limit: int | None = None,
        on_progress: Callable[[int, int], None] | None = None,
        reprocess_all: bool = False,
    ) -> EnrichmentResult:
        """Enrich a batch of tenders.

        Args:
            limit: Maximum tenders to process. Defaults to ingestion_batch_size.
            on_progress: Optional callback(current, total) called after each tender.
                         Can be sync or async (coroutine).
            reprocess_all: If True, re-enrich ALL tenders (even already enriched ones).
        """
        if reprocess_all and limit is None:
            batch_size = 100_000
        else:
            batch_size = limit or settings.ingestion_batch_size
        start = time.time()
        result = EnrichmentResult()

        if not await self.client.is_available():
            logger.error("Ollama not available — skipping enrichment")
            return result

        # Fetch tenders to enrich
        async with get_session() as session:
            repo = TenderRepository(session)
            if reprocess_all:
                tenders = await repo.find_for_enrichment(limit=batch_size)
            else:
                tenders = await repo.find_unenriched(limit=batch_size)

        if not tenders:
            logger.info("No unenriched tenders found")
            return result

        total = len(tenders)
        logger.info(
            "Enriching %d tenders (mode: %s, concurrency: %d)",
            total,
            "GPU" if self.gpu else "sequential",
            self.concurrency,
        )

        # Emit initial progress so dashboard shows total immediately
        if on_progress:
            await self._call_progress(on_progress, 0, total)

        if self.gpu:
            await self._run_parallel(tenders, result, total, on_progress)
        else:
            await self._run_sequential(tenders, result, total, on_progress)

        result.duration_seconds = time.time() - start
        return result

    async def _run_sequential(
        self,
        tenders: list,
        result: EnrichmentResult,
        total: int,
        on_progress: Callable[[int, int], None] | None,
    ) -> None:
        """Process tenders one by one (original behavior)."""
        async with get_session() as session:
            repo = TenderRepository(session)
            for tender in tenders:
                tid = str(tender.id)
                title = tender.title or ""
                result.processed += 1

                self._set_tender_state(tid, "summary", title)
                try:
                    summary = await self._generate_summary(tender)
                    self._set_tender_state(tid, "searchable", title)
                    searchable = await self._generate_searchable(tender)

                    summary = summary[:MAX_SUMMARY_LEN]
                    searchable = searchable[:MAX_SEARCHABLE_LEN]

                    self._set_tender_state(tid, "saving", title)
                    await repo.update_enrichment(
                        tender.id, summary=summary, searchable_text=searchable
                    )
                    await session.commit()
                    result.succeeded += 1
                    self._set_tender_state(tid, "done", title)
                    logger.info(
                        "Enriched tender %d/%d %s: %s",
                        result.processed,
                        total,
                        tender.id,
                        summary[:60],
                    )
                except LLMError as exc:
                    result.failed += 1
                    result.errors.append(f"{tender.id}: {exc}")
                    self._set_tender_state(tid, "failed", title, str(exc))
                    logger.warning("LLM error for tender %s: %s", tender.id, exc)
                except Exception as exc:
                    result.failed += 1
                    result.errors.append(f"{tender.id}: {exc}")
                    self._set_tender_state(tid, "failed", title, str(exc))
                    logger.error(
                        "Unexpected error enriching tender %s: %s",
                        tender.id,
                        exc,
                    )

                if on_progress:
                    await self._call_progress(on_progress, result.processed, total)

    async def _run_parallel(
        self,
        tenders: list,
        result: EnrichmentResult,
        total: int,
        on_progress: Callable[[int, int], None] | None,
    ) -> None:
        """Process tenders in parallel batches using asyncio.gather (GPU mode)."""
        lock = asyncio.Lock()

        for i in range(0, len(tenders), self.concurrency):
            batch = tenders[i : i + self.concurrency]

            # Initialize state for all tenders in this batch
            for t in batch:
                self._set_tender_state(str(t.id), "pending", t.title or "")

            tasks = [
                self._process_one_parallel(t, lock, result, total, on_progress)
                for t in batch
            ]
            await asyncio.gather(*tasks)

    async def _process_one_parallel(
        self,
        tender: "Tender",  # noqa: F821
        lock: asyncio.Lock,
        result: EnrichmentResult,
        total: int,
        on_progress: Callable[[int, int], None] | None,
    ) -> None:
        """Process a single tender with its own DB session (parallel-safe)."""
        tid = str(tender.id)
        title = tender.title or ""
        try:
            self._set_tender_state(tid, "summary", title)
            summary = await self._generate_summary(tender)

            self._set_tender_state(tid, "searchable", title)
            searchable = await self._generate_searchable(tender)

            summary = summary[:MAX_SUMMARY_LEN]
            searchable = searchable[:MAX_SEARCHABLE_LEN]

            self._set_tender_state(tid, "saving", title)
            async with get_session() as session:
                repo = TenderRepository(session)
                await repo.update_enrichment(
                    tender.id, summary=summary, searchable_text=searchable
                )
                await session.commit()

            async with lock:
                result.processed += 1
                result.succeeded += 1
                self._set_tender_state(tid, "done", title)
                logger.info(
                    "Enriched tender %d/%d %s: %s",
                    result.processed,
                    total,
                    tender.id,
                    summary[:60],
                )
                if on_progress:
                    await self._call_progress(on_progress, result.processed, total)

        except LLMError as exc:
            async with lock:
                result.processed += 1
                result.failed += 1
                result.errors.append(f"{tender.id}: {exc}")
                self._set_tender_state(tid, "failed", title, str(exc))
                logger.warning("LLM error for tender %s: %s", tender.id, exc)
                if on_progress:
                    await self._call_progress(on_progress, result.processed, total)

        except Exception as exc:
            async with lock:
                result.processed += 1
                result.failed += 1
                result.errors.append(f"{tender.id}: {exc}")
                self._set_tender_state(tid, "failed", title, str(exc))
                logger.error(
                    "Unexpected error enriching tender %s: %s",
                    tender.id,
                    exc,
                )
                if on_progress:
                    await self._call_progress(on_progress, result.processed, total)

    @staticmethod
    async def _call_progress(
        callback: Callable[[int, int], None], current: int, total: int
    ) -> None:
        """Call a progress callback, awaiting it if it's a coroutine function."""
        ret = callback(current, total)
        if inspect.isawaitable(ret):
            await ret

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
