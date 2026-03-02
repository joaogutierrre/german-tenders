"""Tests for document analysis and storage (Phase 7)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.documents.analyzer import SupplierAnalyzer, SupplierStats, extract_domain


# ── extract_domain ─────────────────────────────────────────────

class TestExtractDomain:
    def test_full_https_url(self) -> None:
        assert extract_domain("https://www.example.de/path") == "www.example.de"

    def test_http_url(self) -> None:
        assert extract_domain("http://portal.vergabe.de/docs") == "portal.vergabe.de"

    def test_no_scheme(self) -> None:
        assert extract_domain("portal.vergabe.de/path") == "portal.vergabe.de"

    def test_with_port(self) -> None:
        assert extract_domain("https://example.de:8080/path") == "example.de:8080"

    def test_empty_string(self) -> None:
        assert extract_domain("") is None

    def test_uppercase_normalized(self) -> None:
        assert extract_domain("https://WWW.EXAMPLE.DE/path") == "www.example.de"


# ── SupplierAnalyzer ───────────────────────────────────────────

class TestSupplierAnalyzer:
    @pytest.mark.asyncio
    async def test_groups_by_domain(self) -> None:
        urls = [
            ("https://portal-a.de/doc1",),
            ("https://portal-a.de/doc2",),
            ("https://portal-b.de/doc3",),
        ]

        with patch("src.documents.analyzer.get_session") as mock_sess:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = urls
            mock_session.execute.return_value = mock_result
            mock_sess.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sess.return_value.__aexit__ = AsyncMock(return_value=False)

            analyzer = SupplierAnalyzer()
            stats = await analyzer.analyze()

            assert len(stats) == 2
            assert stats[0].domain == "portal-a.de"
            assert stats[0].tender_count == 2
            assert stats[1].domain == "portal-b.de"
            assert stats[1].tender_count == 1

    @pytest.mark.asyncio
    async def test_empty_urls(self) -> None:
        with patch("src.documents.analyzer.get_session") as mock_sess:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = []
            mock_session.execute.return_value = mock_result
            mock_sess.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sess.return_value.__aexit__ = AsyncMock(return_value=False)

            analyzer = SupplierAnalyzer()
            stats = await analyzer.analyze()
            assert stats == []

    def test_export_csv(self, tmp_path: Path) -> None:
        stats = [
            SupplierStats(
                domain="portal-a.de",
                tender_count=10,
                percentage=66.7,
                sample_urls=["https://portal-a.de/1"],
            ),
            SupplierStats(
                domain="portal-b.de",
                tender_count=5,
                percentage=33.3,
                sample_urls=["https://portal-b.de/1"],
            ),
        ]

        out = tmp_path / "output" / "suppliers.csv"
        analyzer = SupplierAnalyzer()
        analyzer.export_csv(stats, out)

        assert out.exists()
        lines = out.read_text().strip().splitlines()
        assert len(lines) == 3  # header + 2 rows
        assert "portal-a.de" in lines[1]

    @pytest.mark.asyncio
    async def test_percentage_calculation(self) -> None:
        urls = [
            ("https://a.de/1",),
            ("https://a.de/2",),
            ("https://a.de/3",),
            ("https://b.de/1",),
        ]

        with patch("src.documents.analyzer.get_session") as mock_sess:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = urls
            mock_session.execute.return_value = mock_result
            mock_sess.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sess.return_value.__aexit__ = AsyncMock(return_value=False)

            analyzer = SupplierAnalyzer()
            stats = await analyzer.analyze()

            assert abs(stats[0].percentage - 75.0) < 0.1
            assert abs(stats[1].percentage - 25.0) < 0.1
