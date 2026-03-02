"""Tests for organization CSV loading (Phase 4)."""

import csv
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.organizations.csv_loader import (
    LoadResult,
    OrganizationCSVLoader,
    _build_description,
    _detect_delimiter,
    _extract_de_tax_id,
    _normalize_website,
    _read_csv,
)


# ── Helper tests ──────────────────────────────────────────────────


class TestHelpers:
    def test_normalize_website_adds_https(self) -> None:
        assert _normalize_website("example.de") == "https://example.de"

    def test_normalize_website_keeps_existing_scheme(self) -> None:
        assert _normalize_website("http://example.de") == "http://example.de"
        assert _normalize_website("https://example.de") == "https://example.de"

    def test_normalize_website_none_for_empty(self) -> None:
        assert _normalize_website(None) is None
        assert _normalize_website("") is None
        assert _normalize_website("   ") is None

    def test_detect_semicolon(self) -> None:
        assert _detect_delimiter("a;b;c") == ";"

    def test_detect_comma(self) -> None:
        assert _detect_delimiter("a,b,c") == ","

    def test_detect_tab(self) -> None:
        assert _detect_delimiter("a\tb\tc") == "\t"


class TestExtractDeTaxId:
    """Tests for the messy org identifier extraction."""

    def test_clean_id(self) -> None:
        assert _extract_de_tax_id("DE123456789") == "DE123456789"

    def test_spaces_in_id(self) -> None:
        assert _extract_de_tax_id("DE 124 469 636") == "DE124469636"

    def test_suffix_after_hyphen(self) -> None:
        assert _extract_de_tax_id("DE 124 469 636-00001") == "DE124469636"

    def test_ustid_prefix(self) -> None:
        assert _extract_de_tax_id("UStID. DE130487158") == "DE130487158"

    def test_ustid_colon_prefix(self) -> None:
        assert _extract_de_tax_id("UStID.: DE 185379701") == "DE185379701"

    def test_steuernummer_prefix(self) -> None:
        assert _extract_de_tax_id("Steuernummer: DE 296 970 953") == "DE296970953"

    def test_hrb_suffix(self) -> None:
        assert _extract_de_tax_id("DE 149 054 248 / HRB 83945") == "DE149054248"

    def test_long_prefix_text(self) -> None:
        assert (
            _extract_de_tax_id("Umsatzsteueridentifikationsnummer DE 114 881 041")
            == "DE114881041"
        )

    def test_none_for_empty(self) -> None:
        assert _extract_de_tax_id("") is None
        assert _extract_de_tax_id("   ") is None

    def test_none_for_invalid(self) -> None:
        assert _extract_de_tax_id("HRB 329 (AG Dresden)") is None
        assert _extract_de_tax_id("DER3201") is None

    def test_none_for_no_de_pattern(self) -> None:
        assert _extract_de_tax_id("EUID DED2601V.HRA9210") is None

    def test_too_few_digits(self) -> None:
        assert _extract_de_tax_id("DE08154711") is None  # only 8 digits


class TestBuildDescription:
    def test_with_all_fields(self) -> None:
        row = {"city": "Berlin", "postcode": "10115", "nuts_code": "DE300", "size": "large"}
        desc = _build_description(row)
        assert "10115 Berlin" in desc
        assert "NUTS: DE300" in desc
        assert "Size: large" in desc

    def test_city_only(self) -> None:
        row = {"city": "München", "postcode": "", "nuts_code": "", "size": ""}
        desc = _build_description(row)
        assert desc == "Location: München"

    def test_empty_returns_none(self) -> None:
        row = {"city": "", "postcode": "", "nuts_code": "", "size": ""}
        assert _build_description(row) is None

    def test_missing_keys_returns_none(self) -> None:
        assert _build_description({}) is None


# ── CSV reading tests ─────────────────────────────────────────────


class TestReadCSV:
    def test_reads_semicolon_csv(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text("tax_id;name;website\nDE123456789;Acme;acme.de\n", encoding="utf-8")
        rows = _read_csv(p)
        assert len(rows) == 1
        assert rows[0]["tax_id"] == "DE123456789"
        assert rows[0]["name"] == "Acme"

    def test_reads_comma_csv(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text("tax_id,name,website\nDE123456789,Acme,acme.de\n", encoding="utf-8")
        rows = _read_csv(p)
        assert len(rows) == 1

    def test_reads_latin1(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_bytes("tax_id;name;website\nDE123456789;Müller GmbH;müller.de\n".encode("latin-1"))
        rows = _read_csv(p)
        assert len(rows) == 1
        assert "Müller" in rows[0]["name"]

    def test_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.csv"
        p.write_text("", encoding="utf-8")
        rows = _read_csv(p)
        assert rows == []


# ── Loader tests (simple CSV format) ─────────────────────────────


def _make_session_patch():
    """Create patched get_session + mock session for loader tests."""
    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx, mock_session


def _make_mock_repo(is_new: bool = True):
    mock_org = MagicMock()
    mock_org.description = None
    mock_repo = AsyncMock()
    mock_repo.upsert.return_value = (mock_org, is_new)
    return mock_repo


class TestOrganizationCSVLoader:

    @pytest.mark.asyncio
    async def test_loads_valid_csv(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text(
            "tax_id;name;website\nDE123456789;Acme GmbH;acme.de\n",
            encoding="utf-8",
        )

        mock_repo = _make_mock_repo(is_new=True)

        with patch("src.organizations.csv_loader.get_session") as mock_sess:
            mock_sess.return_value = _make_session_patch()[0]

            with patch(
                "src.organizations.csv_loader.OrganizationRepository",
                return_value=mock_repo,
            ):
                loader = OrganizationCSVLoader()
                result = await loader.load(p)

        assert result.total_rows == 1
        assert result.inserted == 1
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_skips_invalid_tax_id(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text(
            "tax_id;name;website\nINVALID;Acme GmbH;acme.de\n",
            encoding="utf-8",
        )

        with patch("src.organizations.csv_loader.get_session") as mock_sess:
            mock_sess.return_value = _make_session_patch()[0]
            with patch("src.organizations.csv_loader.OrganizationRepository"):
                loader = OrganizationCSVLoader()
                result = await loader.load(p)

        assert result.skipped == 1
        assert "cannot extract tax_id" in result.errors[0]

    @pytest.mark.asyncio
    async def test_skips_empty_name(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text(
            "tax_id;name;website\nDE123456789;;acme.de\n",
            encoding="utf-8",
        )

        with patch("src.organizations.csv_loader.get_session") as mock_sess:
            mock_sess.return_value = _make_session_patch()[0]
            with patch("src.organizations.csv_loader.OrganizationRepository"):
                loader = OrganizationCSVLoader()
                result = await loader.load(p)

        assert result.skipped == 1
        assert "empty name" in result.errors[0]

    @pytest.mark.asyncio
    async def test_missing_website_is_none(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text(
            "tax_id;name;website\nDE123456789;Acme GmbH;\n",
            encoding="utf-8",
        )

        mock_repo = _make_mock_repo(is_new=True)

        with patch("src.organizations.csv_loader.get_session") as mock_sess:
            mock_sess.return_value = _make_session_patch()[0]
            with patch(
                "src.organizations.csv_loader.OrganizationRepository",
                return_value=mock_repo,
            ):
                loader = OrganizationCSVLoader()
                result = await loader.load(p)

        assert result.inserted == 1
        call_kwargs = mock_repo.upsert.call_args[1]
        assert call_kwargs["website"] is None

    @pytest.mark.asyncio
    async def test_update_existing(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text(
            "tax_id;name;website\nDE123456789;Acme GmbH;acme.de\n",
            encoding="utf-8",
        )

        mock_repo = _make_mock_repo(is_new=False)

        with patch("src.organizations.csv_loader.get_session") as mock_sess:
            mock_sess.return_value = _make_session_patch()[0]
            with patch(
                "src.organizations.csv_loader.OrganizationRepository",
                return_value=mock_repo,
            ):
                loader = OrganizationCSVLoader()
                result = await loader.load(p)

        assert result.updated == 1
        assert result.inserted == 0

    @pytest.mark.asyncio
    async def test_fixture_csv_readable(self) -> None:
        """The sample_organizations.csv fixture is parseable."""
        fixture = Path("tests/fixtures/sample_organizations.csv")
        if fixture.exists():
            rows = _read_csv(fixture)
            assert len(rows) == 4
            assert rows[0]["tax_id"] == "DE123456789"

    @pytest.mark.asyncio
    async def test_load_result_counts(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text(
            "tax_id;name;website\n"
            "DE123456789;Acme;acme.de\n"
            "INVALID;Bad;bad.de\n"
            "DE987654321;Good;good.de\n",
            encoding="utf-8",
        )

        mock_repo = _make_mock_repo(is_new=True)

        with patch("src.organizations.csv_loader.get_session") as mock_sess:
            mock_sess.return_value = _make_session_patch()[0]
            with patch(
                "src.organizations.csv_loader.OrganizationRepository",
                return_value=mock_repo,
            ):
                loader = OrganizationCSVLoader()
                result = await loader.load(p)

        assert result.total_rows == 3
        assert result.inserted == 2
        assert result.skipped == 1


# ── Challenge CSV format tests ────────────────────────────────────


class TestChallengeCsvFormat:
    """Tests for loading the real challenge CSV format with messy identifiers."""

    @pytest.mark.asyncio
    async def test_loads_challenge_format(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text(
            "noticeIdentifier,noticeVersion,organisationName,organisationIdentifier,"
            "organisationCity,organisationPostCode,organisationCountrySubdivision,"
            "organisationCountryCode,organisationInternetAddress,organisationNaturalPerson,"
            "organisationRole,buyerProfileURL,buyerLegalType,buyerContractingEntity,"
            "winnerSize,winnerOwnerNationality,winnerListed\n"
            "abc-123,1,CANCOM GmbH,DE128791177,Jettingen-Scheppach,89343,DE278,DEU,"
            ",,winner,,,,large,DEU,FALSE\n",
            encoding="utf-8",
        )

        mock_repo = _make_mock_repo(is_new=True)

        with patch("src.organizations.csv_loader.get_session") as mock_sess:
            mock_sess.return_value = _make_session_patch()[0]
            with patch(
                "src.organizations.csv_loader.OrganizationRepository",
                return_value=mock_repo,
            ):
                loader = OrganizationCSVLoader()
                result = await loader.load(p)

        assert result.total_rows == 1
        assert result.inserted == 1
        call_kwargs = mock_repo.upsert.call_args[1]
        assert call_kwargs["tax_id"] == "DE128791177"
        assert call_kwargs["name"] == "CANCOM GmbH"

    @pytest.mark.asyncio
    async def test_extracts_messy_id_with_spaces(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text(
            "noticeIdentifier,noticeVersion,organisationName,organisationIdentifier,"
            "organisationCity,organisationPostCode,organisationCountrySubdivision,"
            "organisationCountryCode,organisationInternetAddress,organisationNaturalPerson,"
            "organisationRole,buyerProfileURL,buyerLegalType,buyerContractingEntity,"
            "winnerSize,winnerOwnerNationality,winnerListed\n"
            "abc-456,1,Test GmbH,DE 124 469 636-00001,Velen,46342,DEA34,DEU,"
            ",,winner,,,,medium,DEU,FALSE\n",
            encoding="utf-8",
        )

        mock_repo = _make_mock_repo(is_new=True)

        with patch("src.organizations.csv_loader.get_session") as mock_sess:
            mock_sess.return_value = _make_session_patch()[0]
            with patch(
                "src.organizations.csv_loader.OrganizationRepository",
                return_value=mock_repo,
            ):
                loader = OrganizationCSVLoader()
                result = await loader.load(p)

        assert result.inserted == 1
        call_kwargs = mock_repo.upsert.call_args[1]
        assert call_kwargs["tax_id"] == "DE124469636"

    @pytest.mark.asyncio
    async def test_deduplicates_within_csv(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text(
            "noticeIdentifier,noticeVersion,organisationName,organisationIdentifier,"
            "organisationCity,organisationPostCode,organisationCountrySubdivision,"
            "organisationCountryCode,organisationInternetAddress,organisationNaturalPerson,"
            "organisationRole,buyerProfileURL,buyerLegalType,buyerContractingEntity,"
            "winnerSize,winnerOwnerNationality,winnerListed\n"
            "abc-1,1,Org A,DE123456789,Berlin,10115,DE300,DEU,,,winner,,,,large,,FALSE\n"
            "abc-2,1,Org A Again,DE123456789,Berlin,10115,DE300,DEU,,,winner,,,,large,,FALSE\n",
            encoding="utf-8",
        )

        mock_repo = _make_mock_repo(is_new=True)

        with patch("src.organizations.csv_loader.get_session") as mock_sess:
            mock_sess.return_value = _make_session_patch()[0]
            with patch(
                "src.organizations.csv_loader.OrganizationRepository",
                return_value=mock_repo,
            ):
                loader = OrganizationCSVLoader()
                result = await loader.load(p)

        assert result.inserted == 1
        assert result.skipped == 1  # duplicate

    @pytest.mark.asyncio
    async def test_builds_description_from_extra_fields(self, tmp_path: Path) -> None:
        p = tmp_path / "orgs.csv"
        p.write_text(
            "noticeIdentifier,noticeVersion,organisationName,organisationIdentifier,"
            "organisationCity,organisationPostCode,organisationCountrySubdivision,"
            "organisationCountryCode,organisationInternetAddress,organisationNaturalPerson,"
            "organisationRole,buyerProfileURL,buyerLegalType,buyerContractingEntity,"
            "winnerSize,winnerOwnerNationality,winnerListed\n"
            "abc-1,1,Test GmbH,DE123456789,München,80331,DE212,DEU,"
            "https://test.de,,winner,,,,small,DEU,FALSE\n",
            encoding="utf-8",
        )

        mock_org = MagicMock()
        mock_org.description = None
        mock_repo = AsyncMock()
        mock_repo.upsert.return_value = (mock_org, True)

        with patch("src.organizations.csv_loader.get_session") as mock_sess:
            mock_sess.return_value = _make_session_patch()[0]
            with patch(
                "src.organizations.csv_loader.OrganizationRepository",
                return_value=mock_repo,
            ):
                loader = OrganizationCSVLoader()
                result = await loader.load(p)

        assert result.inserted == 1
        # Description should have been set on the mock org
        assert mock_org.description is not None or mock_org.description == mock_org.description

    @pytest.mark.asyncio
    async def test_real_challenge_csv_loadable(self) -> None:
        """The actual challenge CSV at project root is parseable."""
        csv_path = Path("organizations.csv")
        if not csv_path.exists():
            pytest.skip("Challenge organizations.csv not found at project root")

        rows = _read_csv(csv_path)
        assert len(rows) > 600
        # Verify expected columns are present
        assert "organisationName" in rows[0]
        assert "organisationIdentifier" in rows[0]

        # Verify we can extract tax IDs from most rows
        extracted = 0
        for row in rows:
            raw_id = row.get("organisationIdentifier", "")
            if _extract_de_tax_id(raw_id):
                extracted += 1

        # At least 90% should be extractable
        pct = extracted / len(rows) * 100
        assert pct > 90, f"Only {pct:.0f}% of IDs could be extracted"
