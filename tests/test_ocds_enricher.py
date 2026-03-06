"""Tests for OCDS document URL enrichment."""

import io
import json
import zipfile

import pytest

from src.ingestion.ocds_enricher import (
    OCDSEnrichResult,
    _extract_notice_id,
    _should_update_url,
    parse_ocds_zip,
)


def _make_ocds_zip(releases: list[dict], filename: str = "notices.json") -> bytes:
    """Create a synthetic OCDS ZIP for testing."""
    data = {"releases": releases}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, json.dumps(data))
    return buf.getvalue()


def _make_release(
    notice_id: str,
    doc_urls: list[str] | None = None,
    ocid: str | None = None,
) -> dict:
    """Create a minimal OCDS release with documents."""
    release: dict = {
        "id": notice_id,
        "tender": {
            "id": notice_id,
            "title": f"Test Tender {notice_id}",
        },
    }
    if ocid:
        release["ocid"] = ocid
    if doc_urls is not None:
        release["tender"]["documents"] = [
            {"id": f"DOC-{i}", "url": url, "language": "DEU"}
            for i, url in enumerate(doc_urls, 1)
        ]
    return release


# ── parse_ocds_zip tests ──────────────────────────────────────────


class TestParseOCDSZip:
    """Tests for parse_ocds_zip function."""

    def test_parses_valid_ocds_zip(self) -> None:
        """Valid OCDS ZIP returns document URLs keyed by notice ID."""
        releases = [
            _make_release("abc-123", ["https://portal.example.de/abc"]),
            _make_release("def-456", ["https://portal.example.de/def"]),
        ]
        result = parse_ocds_zip(_make_ocds_zip(releases))

        assert "abc-123" in result
        assert "def-456" in result
        assert result["abc-123"] == ["https://portal.example.de/abc"]

    def test_empty_bytes_returns_empty_dict(self) -> None:
        """Empty input returns empty dict."""
        assert parse_ocds_zip(b"") == {}

    def test_invalid_zip_returns_empty_dict(self) -> None:
        """Invalid ZIP returns empty dict without crashing."""
        assert parse_ocds_zip(b"not a zip file") == {}

    def test_missing_documents_array(self) -> None:
        """Release without tender.documents still parses (no error)."""
        releases = [_make_release("no-docs")]
        result = parse_ocds_zip(_make_ocds_zip(releases))
        assert "no-docs" not in result

    def test_empty_documents_array(self) -> None:
        """Release with empty documents array returns no URLs."""
        releases = [_make_release("empty-docs", doc_urls=[])]
        result = parse_ocds_zip(_make_ocds_zip(releases))
        assert "empty-docs" not in result

    def test_multiple_documents_per_notice(self) -> None:
        """All document URLs are collected for a single notice."""
        releases = [
            _make_release(
                "multi-doc",
                [
                    "https://portal.example.de/page1",
                    "https://portal.example.de/page2",
                    "https://portal.example.de/page3",
                ],
            )
        ]
        result = parse_ocds_zip(_make_ocds_zip(releases))
        assert len(result["multi-doc"]) == 3

    def test_deduplicates_urls(self) -> None:
        """Same URL appearing multiple times is deduplicated."""
        releases = [
            _make_release(
                "dup-url",
                [
                    "https://portal.example.de/same",
                    "https://portal.example.de/same",
                    "https://portal.example.de/different",
                ],
            )
        ]
        result = parse_ocds_zip(_make_ocds_zip(releases))
        assert len(result["dup-url"]) == 2

    def test_skips_empty_url_strings(self) -> None:
        """Documents with empty URL strings are ignored."""
        releases = [
            {
                "id": "blank-url",
                "tender": {
                    "id": "blank-url",
                    "documents": [
                        {"id": "DOC-1", "url": ""},
                        {"id": "DOC-2", "url": "   "},
                        {"id": "DOC-3", "url": "https://valid.de/doc"},
                    ],
                },
            }
        ]
        result = parse_ocds_zip(_make_ocds_zip(releases))
        assert result["blank-url"] == ["https://valid.de/doc"]

    def test_handles_multiple_json_files(self) -> None:
        """ZIP with multiple JSON files processes all of them."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "batch1.json",
                json.dumps(
                    {
                        "releases": [
                            _make_release("n1", ["https://a.de/1"]),
                        ]
                    }
                ),
            )
            zf.writestr(
                "batch2.json",
                json.dumps(
                    {
                        "releases": [
                            _make_release("n2", ["https://b.de/2"]),
                        ]
                    }
                ),
            )
        result = parse_ocds_zip(buf.getvalue())
        assert "n1" in result
        assert "n2" in result

    def test_ignores_non_json_files(self) -> None:
        """Non-JSON files in the ZIP are skipped."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "notices.json",
                json.dumps(
                    {
                        "releases": [
                            _make_release("valid", ["https://x.de/1"]),
                        ]
                    }
                ),
            )
            zf.writestr("readme.txt", "This is not JSON")
        result = parse_ocds_zip(buf.getvalue())
        assert "valid" in result
        assert len(result) == 1


# ── _extract_notice_id tests ──────────────────────────────────────


class TestExtractNoticeId:
    """Tests for notice ID extraction from OCDS releases."""

    def test_from_release_id(self) -> None:
        """Extracts notice ID from release.id."""
        assert _extract_notice_id({"id": "abc-123"}) == "abc-123"

    def test_from_tender_id(self) -> None:
        """Falls back to tender.id when release.id is missing."""
        assert (
            _extract_notice_id({"tender": {"id": "tender-42"}}) == "tender-42"
        )

    def test_from_ocid(self) -> None:
        """Parses notice ID from ocid field."""
        release = {"ocid": "ocds-prefix-my-notice-id"}
        assert _extract_notice_id(release) == "my-notice-id"

    def test_returns_none_for_empty_release(self) -> None:
        """Returns None when no identifiers found."""
        assert _extract_notice_id({}) is None


# ── _should_update_url tests ──────────────────────────────────────


class TestShouldUpdateUrl:
    """Tests for URL update heuristic."""

    def test_updates_when_current_is_none(self) -> None:
        """Should update when current URL is None."""
        assert _should_update_url(None, "https://portal.de/doc") is True

    def test_updates_when_current_is_empty(self) -> None:
        """Should update when current URL is empty."""
        assert _should_update_url("", "https://portal.de/doc") is True

    def test_updates_when_current_is_generic(self) -> None:
        """Should update when current URL has a short path (generic site)."""
        assert (
            _should_update_url(
                "https://www.example.de/",
                "https://portal.de/dashboards/abc-123-uuid",
            )
            is True
        )

    def test_no_update_when_same_url(self) -> None:
        """Should not update when URLs are the same."""
        url = "https://portal.de/doc/123"
        assert _should_update_url(url, url) is False

    def test_updates_when_ocds_has_longer_path(self) -> None:
        """Should update when OCDS URL has a more specific path."""
        assert (
            _should_update_url(
                "https://www.site.de/portal",
                "https://www.site.de/portal/dashboards/uuid-here",
            )
            is True
        )

    def test_no_update_when_current_is_specific(self) -> None:
        """Should not update when current URL is already specific."""
        assert (
            _should_update_url(
                "https://portal.de/dashboards/very-long-uuid-path-here",
                "https://portal.de/short",
            )
            is False
        )
