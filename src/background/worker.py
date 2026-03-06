"""Standalone worker script — executed as a subprocess to run background jobs.

Usage: python -m src.background.worker <job_id>
"""

import asyncio
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

# Ensure project root is on sys.path when run as a standalone script.
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.db.repositories import BackgroundJobRepository
from src.db.session import get_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def _update_progress(job_id: UUID, current: int, total: int) -> None:
    """Update job progress in the database."""
    async with get_session() as session:
        repo = BackgroundJobRepository(session)
        await repo.update_progress(job_id, current, total)


async def _run_enrichment(job_id: UUID, params: dict) -> dict:
    """Execute the enrichment pipeline for a background job."""
    from src.ai.llm_client import OllamaClient
    from src.config import settings
    from src.ingestion.enrichment import EnrichmentPipeline

    limit = params.get("limit")
    gpu = params.get("gpu", False)
    reprocess_all = params.get("reprocess_all", False)
    client = OllamaClient(model=settings.ollama_model_fast)

    # State file for per-tender inspect view
    log_dir = Path(__file__).resolve().parent.parent.parent / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    state_file = log_dir / f"worker-{job_id}.state"

    async def on_progress(current: int, total: int) -> None:
        await _update_progress(job_id, current, total)

    pipeline = EnrichmentPipeline(client, gpu=gpu, state_file=state_file)
    result = await pipeline.run(limit=limit, on_progress=on_progress, reprocess_all=reprocess_all)

    return {
        "processed": result.processed,
        "succeeded": result.succeeded,
        "failed": result.failed,
        "skipped": result.skipped,
        "duration_seconds": round(result.duration_seconds, 1),
    }


async def _run_docs_download(job_id: UUID, params: dict) -> dict:
    """Execute the document download pipeline for a background job."""
    from src.documents.downloader import DocumentDownloader

    domain = params["domain"]
    limit = params.get("limit", 100)

    async def on_progress(current: int, total: int) -> None:
        await _update_progress(job_id, current, total)

    downloader = DocumentDownloader()
    result = await downloader.download_for_supplier(
        domain, limit=limit, on_progress=on_progress
    )

    return {
        "tenders_processed": result.tenders_processed,
        "documents_downloaded": result.documents_downloaded,
        "documents_failed": result.documents_failed,
        "total_bytes": result.total_bytes,
    }


async def _run_embedding(job_id: UUID, params: dict) -> dict:
    """Execute the embedding generation pipeline for a background job."""
    from src.search.embeddings import generate_tender_embeddings

    limit = params.get("limit", 500)

    async def on_progress(current: int, total: int) -> None:
        await _update_progress(job_id, current, total)

    count = await generate_tender_embeddings(limit=limit, on_progress=on_progress)

    return {"embedded": count}


DISPATCHERS = {
    "enrichment": _run_enrichment,
    "docs_download": _run_docs_download,
    "embedding": _run_embedding,
}


async def run_job(job_id: UUID) -> None:
    """Main entry point — load job, dispatch, update status."""
    # Load job and validate
    async with get_session() as session:
        repo = BackgroundJobRepository(session)
        job = await repo.find_by_id(job_id)
        if not job:
            logger.error("Job %s not found", job_id)
            return
        if job.status != "pending":
            logger.error("Job %s has status %s, expected pending", job_id, job.status)
            return

        # Mark as running
        await repo.update_status(
            job_id,
            "running",
            pid=os.getpid(),
            started_at=datetime.utcnow(),
        )
        job_type = job.job_type
        params = job.params

    dispatcher = DISPATCHERS.get(job_type)
    if not dispatcher:
        async with get_session() as session:
            repo = BackgroundJobRepository(session)
            await repo.update_status(
                job_id,
                "failed",
                error_message=f"Unknown job type: {job_type}",
                completed_at=datetime.utcnow(),
            )
        return

    try:
        result_summary = await dispatcher(job_id, params)
        async with get_session() as session:
            repo = BackgroundJobRepository(session)
            await repo.update_status(
                job_id,
                "completed",
                result_summary=result_summary,
                completed_at=datetime.utcnow(),
            )
        logger.info("Job %s completed: %s", job_id, result_summary)
    except Exception as exc:
        logger.error("Job %s failed: %s", job_id, exc)
        async with get_session() as session:
            repo = BackgroundJobRepository(session)
            await repo.update_status(
                job_id,
                "failed",
                error_message=str(exc),
                completed_at=datetime.utcnow(),
            )


def main() -> None:
    """CLI entry point for the worker script."""
    if len(sys.argv) != 2:
        logger.error("Usage: python -m src.background.worker <job_id>")
        sys.exit(1)

    job_id = UUID(sys.argv[1])
    logger.info("Worker starting for job %s (PID %d)", job_id, os.getpid())
    asyncio.run(run_job(job_id))


if __name__ == "__main__":
    main()
