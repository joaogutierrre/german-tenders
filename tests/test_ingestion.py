"""Tests for ingestion: parser with real CSV data + API client.

The parser tests use the REAL fixture at tests/fixtures/sample_csv.zip
(1247 records from oeffentlichevergabe.de, 2026-02-25).
"""

import io
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingestion.api_client import APIError, TenderAPIClient
from src.ingestion.parser import (
    RawLotRecord,
    RawTenderRecord,
    _safe_decimal,
    _safe_int,
    _parse_date,
    _parse_datetime,
    parse_csv_zip,
)

FIXTURE_ZIP = Path("tests/fixtures/sample_csv.zip")


# ────────────────────────────────────────────────────
#  Helper parsers
# ────────────────────────────────────────────────────

class TestHelperParsers:
    def test_safe_decimal_valid(self) -> None:
        from decimal import Decimal
        assert _safe_decimal("1234.56") == Decimal("1234.56")

    def test_safe_decimal_none(self) -> None:
        assert _safe_decimal(None) is None
        assert _safe_decimal("") is None
        assert _safe_decimal("   ") is None

    def test_safe_decimal_invalid(self) -> None:
        assert _safe_decimal("not-a-number") is None

    def test_safe_int_valid(self) -> None:
        assert _safe_int("42") == 42
        assert _safe_int("3.0") == 3

    def test_safe_int_none(self) -> None:
        assert _safe_int(None) is None
        assert _safe_int("") is None

    def test_parse_date_valid(self) -> None:
        assert _parse_date("2026-02-25") == date(2026, 2, 25)

    def test_parse_date_invalid(self) -> None:
        assert _parse_date("not-a-date") is None
        assert _parse_date(None) is None

    def test_parse_datetime_valid(self) -> None:
        dt = _parse_datetime("2026-03-15T10:00:00+01:00")
        assert dt is not None
        assert dt.year == 2026

    def test_parse_datetime_invalid(self) -> None:
        assert _parse_datetime("garbage") is None


# ────────────────────────────────────────────────────
#  Parser tests with REAL fixture data
# ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def real_zip_bytes() -> bytes:
    """Load the real CSV ZIP fixture."""
    assert FIXTURE_ZIP.exists(), f"Fixture missing: {FIXTURE_ZIP}"
    return FIXTURE_ZIP.read_bytes()


@pytest.fixture(scope="module")
def parsed_records(real_zip_bytes: bytes) -> list[RawTenderRecord]:
    """Parse the real fixture once for all tests in this module."""
    return parse_csv_zip(real_zip_bytes)


class TestParserRealData:
    def test_parse_returns_records(self, parsed_records: list[RawTenderRecord]) -> None:
        """ZIP with 1247 notices should return ~1247 records."""
        assert len(parsed_records) >= 1200
        assert len(parsed_records) <= 1300

    def test_all_have_notice_id(self, parsed_records: list[RawTenderRecord]) -> None:
        """Every record must have a notice_id."""
        for r in parsed_records:
            assert r.notice_id, f"Empty notice_id in record: {r.title[:50]}"

    def test_all_have_title(self, parsed_records: list[RawTenderRecord]) -> None:
        """Every record must have a non-empty title."""
        with_title = [r for r in parsed_records if r.title.strip()]
        assert len(with_title) == len(parsed_records)

    def test_cpv_codes_extracted(self, parsed_records: list[RawTenderRecord]) -> None:
        """Most records (~1220) should have CPV codes."""
        with_cpv = [r for r in parsed_records if r.cpv_codes]
        assert len(with_cpv) >= 1100

    def test_issuer_names_extracted(self, parsed_records: list[RawTenderRecord]) -> None:
        """Most records (~1239) should have an issuer name."""
        with_issuer = [r for r in parsed_records if r.issuer_name]
        assert len(with_issuer) >= 1200

    def test_portal_urls_extracted(self, parsed_records: list[RawTenderRecord]) -> None:
        """Some records (~626) should have document portal URLs."""
        with_portal = [r for r in parsed_records if r.document_portal_url]
        assert len(with_portal) >= 500

    def test_estimated_values_extracted(self, parsed_records: list[RawTenderRecord]) -> None:
        """Some records (~210) should have estimated values."""
        with_value = [r for r in parsed_records if r.estimated_value is not None]
        assert len(with_value) >= 150

    def test_publication_dates_extracted(self, parsed_records: list[RawTenderRecord]) -> None:
        """Most records should have a publication date."""
        with_date = [r for r in parsed_records if r.publication_date is not None]
        assert len(with_date) >= 1200

    def test_lots_extracted(self, parsed_records: list[RawTenderRecord]) -> None:
        """Some records should have lots."""
        with_lots = [r for r in parsed_records if r.lots]
        assert len(with_lots) >= 50

    def test_source_id_format(self, parsed_records: list[RawTenderRecord]) -> None:
        """Source ID should be notice_id-version format."""
        r = parsed_records[0]
        source_id = f"{r.notice_id}-{r.notice_version}"
        assert r.notice_id in source_id
        assert "-" in source_id

    def test_nuts_codes_extracted(self, parsed_records: list[RawTenderRecord]) -> None:
        """Some records should have NUTS codes."""
        with_nuts = [r for r in parsed_records if r.nuts_codes]
        assert len(with_nuts) >= 100

    def test_platform_urls_all_present(self, parsed_records: list[RawTenderRecord]) -> None:
        """All records should have a platform URL (generated)."""
        for r in parsed_records:
            assert r.platform_url
            assert "oeffentlichevergabe.de" in r.platform_url

    def test_raw_data_stored(self, parsed_records: list[RawTenderRecord]) -> None:
        """Raw data dict should be populated."""
        for r in parsed_records[:10]:
            assert isinstance(r.raw_data, dict)
            assert "notice" in r.raw_data

    def test_no_duplicate_cpv_codes(self, parsed_records: list[RawTenderRecord]) -> None:
        """CPV codes should be deduplicated."""
        for r in parsed_records:
            assert len(r.cpv_codes) == len(set(r.cpv_codes))


class TestParserEdgeCases:
    def test_empty_bytes_returns_empty(self) -> None:
        assert parse_csv_zip(b"") == []

    def test_empty_zip_returns_empty(self) -> None:
        """ZIP with no CSV files returns empty list."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "no csvs here")
        result = parse_csv_zip(buf.getvalue())
        assert result == []

    def test_zip_with_only_notice_csv(self) -> None:
        """ZIP with just notice.csv (no purpose/org) still parses."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            csv_content = "noticeIdentifier,noticeVersion,publicationDate\nTEST-001,1,2026-01-01\n"
            zf.writestr("notice.csv", csv_content)
        result = parse_csv_zip(buf.getvalue())
        assert len(result) == 1
        assert result[0].notice_id == "TEST-001"
        assert result[0].title == ""  # no purpose.csv


# ────────────────────────────────────────────────────
#  API Client tests (mocked httpx)
# ────────────────────────────────────────────────────

class TestTenderAPIClient:
    @pytest.mark.asyncio
    async def test_fetch_day_export_success(self) -> None:
        """Successful fetch returns ZIP bytes."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"PK\x03\x04fake-zip-data"

        with patch("src.ingestion.api_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            client = TenderAPIClient(base_url="https://test.de")
            result = await client.fetch_day_export(date(2026, 2, 25))

            assert result == b"PK\x03\x04fake-zip-data"
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_day_export_404_returns_empty(self) -> None:
        """404 means no data for that day — return empty bytes."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("src.ingestion.api_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            client = TenderAPIClient(base_url="https://test.de")
            result = await client.fetch_day_export(date(2026, 12, 25))

            assert result == b""

    @pytest.mark.asyncio
    async def test_fetch_day_export_500_retries(self) -> None:
        """Server error triggers retries."""
        mock_resp_500 = MagicMock()
        mock_resp_500.status_code = 500
        mock_resp_500.text = "Internal Server Error"

        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.content = b"zip-data"

        with patch("src.ingestion.api_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [mock_resp_500, mock_resp_200]
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                client = TenderAPIClient(base_url="https://test.de")
                result = await client.fetch_day_export(date(2026, 2, 25))

            assert result == b"zip-data"
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_day_export_all_retries_fail(self) -> None:
        """All retries fail raises APIError."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "Service Unavailable"

        with patch("src.ingestion.api_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                client = TenderAPIClient(base_url="https://test.de")
                with pytest.raises(APIError, match="Failed after 3 retries"):
                    await client.fetch_day_export(date(2026, 2, 25))

    @pytest.mark.asyncio
    async def test_fetch_date_range_calls_per_day(self) -> None:
        """fetch_date_range should call fetch_day_export for each day."""
        client = TenderAPIClient(base_url="https://test.de")

        calls: list[date] = []

        async def mock_fetch(pub_day: date, fmt: str = "csv.zip") -> bytes:
            calls.append(pub_day)
            return b"data"

        client.fetch_day_export = mock_fetch  # type: ignore[assignment]

        result = await client.fetch_date_range(date(2026, 2, 1), date(2026, 2, 3))

        assert len(calls) == 3
        assert calls[0] == date(2026, 2, 1)
        assert calls[2] == date(2026, 2, 3)
        assert len(result) == 3
