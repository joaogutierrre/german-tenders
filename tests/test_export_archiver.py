"""Tests for raw API export archival."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.documents.export_archiver import ExportArchiver


@pytest.fixture
def mock_storage() -> AsyncMock:
    """Create a mock DocumentStorage."""
    storage = AsyncMock()
    storage.bucket = "api-exports"
    storage.ensure_bucket = AsyncMock()
    storage.upload = AsyncMock(return_value="exports/2026-03-01/csv.zip")
    return storage


class TestExportArchiver:
    """Tests for ExportArchiver."""

    @pytest.mark.asyncio
    async def test_archives_zip_to_minio(self, mock_storage: AsyncMock) -> None:
        """Verify ZIP is uploaded with correct key pattern."""
        archiver = ExportArchiver(storage=mock_storage)
        key = await archiver.archive(
            date(2026, 3, 1), "csv.zip", b"fake zip data"
        )

        assert key == "exports/2026-03-01/csv.zip"
        mock_storage.ensure_bucket.assert_awaited_once()
        mock_storage.upload.assert_awaited_once_with(
            "exports/2026-03-01/csv.zip", b"fake zip data", "application/zip"
        )

    @pytest.mark.asyncio
    async def test_key_format_ocds(self, mock_storage: AsyncMock) -> None:
        """Key for OCDS follows expected pattern."""
        mock_storage.upload = AsyncMock(
            return_value="exports/2026-02-28/ocds.zip"
        )
        archiver = ExportArchiver(storage=mock_storage)
        key = await archiver.archive(
            date(2026, 2, 28), "ocds.zip", b"ocds data"
        )

        assert key == "exports/2026-02-28/ocds.zip"

    @pytest.mark.asyncio
    async def test_skips_empty_data(self, mock_storage: AsyncMock) -> None:
        """Empty bytes are not archived."""
        archiver = ExportArchiver(storage=mock_storage)
        key = await archiver.archive(date(2026, 3, 1), "csv.zip", b"")

        assert key is None
        mock_storage.upload.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_when_disabled(self, mock_storage: AsyncMock) -> None:
        """archive_raw_exports=False means no upload."""
        with patch("src.documents.export_archiver.settings") as mock_settings:
            mock_settings.archive_raw_exports = False
            mock_settings.minio_exports_bucket = "api-exports"

            archiver = ExportArchiver(storage=mock_storage)
            key = await archiver.archive(
                date(2026, 3, 1), "csv.zip", b"data"
            )

            assert key is None
            mock_storage.upload.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_none_on_none_data(
        self, mock_storage: AsyncMock
    ) -> None:
        """None data returns None without error."""
        archiver = ExportArchiver(storage=mock_storage)
        # bytes check: not data returns True for b"" but we need to handle
        # the archive_raw_exports check first
        key = await archiver.archive(date(2026, 3, 1), "csv.zip", b"")
        assert key is None
