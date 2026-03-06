"""Archive raw API export ZIPs in a dedicated MinIO bucket."""

import logging
from datetime import date

from src.config import settings
from src.documents.storage import DocumentStorage

logger = logging.getLogger(__name__)


class ExportArchiver:
    """Archive raw API export ZIPs in MinIO for reference.

    Stores CSV and OCDS bulk exports in a separate bucket so they
    can be reprocessed later without re-fetching from the API.
    """

    def __init__(self, storage: DocumentStorage | None = None) -> None:
        self.storage = storage or DocumentStorage(
            bucket=settings.minio_exports_bucket,
        )

    async def archive(
        self, pub_day: date, fmt: str, data: bytes
    ) -> str | None:
        """Store a raw export ZIP in MinIO.

        Args:
            pub_day: The publication date this export covers.
            fmt: Export format (e.g. ``csv.zip``, ``ocds.zip``).
            data: Raw ZIP bytes.

        Returns:
            The storage key, or ``None`` if archival is disabled or
            data is empty.
        """
        if not settings.archive_raw_exports or not data:
            return None

        await self.storage.ensure_bucket()
        key = f"exports/{pub_day.isoformat()}/{fmt}"
        content_type = "application/zip"
        await self.storage.upload(key, data, content_type)
        logger.info(
            "Archived %s (%d bytes) to bucket %s",
            key,
            len(data),
            self.storage.bucket,
        )
        return key
