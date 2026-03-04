"""Background job manager — create jobs, spawn workers, cancel, cleanup."""

import logging
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID

from src.db.models import BackgroundJob
from src.db.repositories import BackgroundJobRepository
from src.db.session import get_session

logger = logging.getLogger(__name__)

WORKER_SCRIPT = Path(__file__).resolve().parent / "worker.py"


class BackgroundJobManager:
    """Manage background jobs: create, spawn, cancel, list."""

    async def create_job(self, job_type: str, params: dict) -> UUID:
        """Create a job row with status=pending and return its ID."""
        async with get_session() as session:
            repo = BackgroundJobRepository(session)
            job = await repo.create(job_type, params)
            job_id = job.id
        return job_id

    def spawn_worker(self, job_id: UUID) -> int:
        """Spawn a detached subprocess to execute the job. Returns PID."""
        kwargs: dict = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            kwargs["start_new_session"] = True

        proc = subprocess.Popen(
            [sys.executable, str(WORKER_SCRIPT), str(job_id)],
            stdout=open(os.devnull, "w"),
            stderr=open(os.devnull, "w"),
            **kwargs,
        )
        logger.info("Spawned worker PID %d for job %s", proc.pid, job_id)
        return proc.pid

    async def cancel_job(self, job_id: UUID) -> None:
        """Cancel a running job by terminating its process."""
        import signal

        async with get_session() as session:
            repo = BackgroundJobRepository(session)
            job = await repo.find_by_id(job_id)
            if not job:
                return
            if job.status not in ("pending", "running"):
                return

            if job.pid:
                try:
                    if sys.platform == "win32":
                        os.kill(job.pid, signal.SIGTERM)
                    else:
                        os.kill(job.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                except OSError as exc:
                    logger.warning("Failed to kill PID %d: %s", job.pid, exc)

            await repo.update_status(job_id, "cancelled")

    async def list_jobs(
        self, status_filter: str | None = None
    ) -> list[BackgroundJob]:
        """List jobs from DB, optionally filtered by status."""
        async with get_session() as session:
            repo = BackgroundJobRepository(session)
            return await repo.find_all(status_filter)

    async def cleanup_stale(self) -> int:
        """Detect running jobs whose PID no longer exists and mark as failed.

        Returns:
            Number of stale jobs detected.
        """
        count = 0
        async with get_session() as session:
            repo = BackgroundJobRepository(session)
            active = await repo.find_active()
            for job in active:
                if job.status == "running" and job.pid:
                    if not _pid_exists(job.pid):
                        await repo.update_status(
                            job.id,
                            "failed",
                            error_message="Worker process terminated unexpectedly",
                        )
                        count += 1
                        logger.warning(
                            "Stale job %s (PID %d) marked as failed",
                            job.id, job.pid,
                        )
        return count


def _pid_exists(pid: int) -> bool:
    """Check if a process with given PID exists."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            SYNCHRONIZE = 0x00100000
            handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # process exists but we don't have permission
