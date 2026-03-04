"""Tests for the i18n (internationalisation) module."""

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest


# ── Translation function tests ─────────────────────────────────────────────


class TestTranslationFunction:
    """Tests for the ``t()`` function."""

    def setup_method(self) -> None:
        """Reset i18n module state before each test."""
        import src.i18n as i18n
        i18n._loaded = False
        i18n._current_locale = i18n.DEFAULT_LOCALE
        i18n._catalog = {}
        i18n._fallback = {}

    def test_t_returns_english_by_default(self) -> None:
        from src.i18n import set_locale, t
        set_locale("en-US")
        assert t("welcome.tagline") == "German Procurement Intelligence Platform"

    def test_t_formats_kwargs(self) -> None:
        from src.i18n import set_locale, t
        set_locale("en-US")
        result = t("ingest.progress_days", days=7)
        assert "7" in result
        assert "days" not in result or "7 days" in result

    def test_t_falls_back_to_english_for_missing_key(self) -> None:
        from src.i18n import set_locale, t
        set_locale("pt-BR")
        # All keys exist in all catalogs, so test by removing one
        import src.i18n as i18n
        original = i18n._catalog.pop("welcome.tagline", None)
        result = t("welcome.tagline")
        assert result == "German Procurement Intelligence Platform"  # fallback to en-US
        if original:
            i18n._catalog["welcome.tagline"] = original

    def test_t_returns_key_on_total_miss(self) -> None:
        from src.i18n import set_locale, t
        set_locale("en-US")
        assert t("nonexistent.key.here") == "nonexistent.key.here"

    def test_t_handles_format_error_gracefully(self) -> None:
        from src.i18n import set_locale, t
        set_locale("en-US")
        # ingest.done expects {fetched}, {inserted}, etc. — calling without them
        result = t("ingest.done")
        assert isinstance(result, str)
        # Should return the raw value (with placeholders still in it)
        assert "{fetched}" in result

    def test_set_locale_invalid_falls_back(self) -> None:
        from src.i18n import set_locale, get_locale
        set_locale("xx-XX")
        assert get_locale() == "en-US"

    def test_t_with_pt_br_locale(self) -> None:
        from src.i18n import set_locale, t
        set_locale("pt-BR")
        result = t("welcome.tagline")
        assert result != "welcome.tagline"  # not the raw key
        assert result != ""

    def test_t_with_de_de_locale(self) -> None:
        from src.i18n import set_locale, t
        set_locale("de-DE")
        result = t("welcome.tagline")
        assert result != "welcome.tagline"
        assert result != ""

    def test_t_with_pt_pt_locale(self) -> None:
        from src.i18n import set_locale, t
        set_locale("pt-PT")
        result = t("welcome.tagline")
        assert result != "welcome.tagline"
        assert result != ""


# ── Config file persistence tests ──────────────────────────────────────────


class TestLocaleConfig:
    """Tests for config file persistence."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        import src.i18n as i18n
        i18n._loaded = False

        with patch.object(i18n, "CONFIG_DIR", tmp_path), \
             patch.object(i18n, "CONFIG_FILE", tmp_path / "config.json"):
            i18n.save_locale("pt-BR")
            assert (tmp_path / "config.json").exists()

            data = json.loads((tmp_path / "config.json").read_text())
            assert data["locale"] == "pt-BR"

            i18n.load_locale()
            assert i18n.get_locale() == "pt-BR"

    def test_load_missing_file_defaults_to_english(self, tmp_path: Path) -> None:
        import src.i18n as i18n
        i18n._loaded = False

        with patch.object(i18n, "CONFIG_FILE", tmp_path / "nonexistent.json"):
            i18n.load_locale()
            assert i18n.get_locale() == "en-US"

    def test_load_corrupt_json_defaults_to_english(self, tmp_path: Path) -> None:
        import src.i18n as i18n
        i18n._loaded = False

        bad_file = tmp_path / "config.json"
        bad_file.write_text("NOT VALID JSON {{{{", encoding="utf-8")

        with patch.object(i18n, "CONFIG_FILE", bad_file):
            i18n.load_locale()
            assert i18n.get_locale() == "en-US"

    def test_save_preserves_other_keys(self, tmp_path: Path) -> None:
        import src.i18n as i18n

        config_file = tmp_path / "config.json"
        config_file.write_text('{"theme": "dark", "locale": "en-US"}', encoding="utf-8")

        with patch.object(i18n, "CONFIG_DIR", tmp_path), \
             patch.object(i18n, "CONFIG_FILE", config_file):
            i18n.save_locale("de-DE")

        data = json.loads(config_file.read_text())
        assert data["locale"] == "de-DE"
        assert data["theme"] == "dark"  # preserved


# ── Catalog completeness tests ─────────────────────────────────────────────


class TestCatalogCompleteness:
    """Verify all locale files have the same keys as en-US."""

    def _get_catalogs(self) -> dict[str, dict[str, str]]:
        from src.i18n.en_us import STRINGS as en
        from src.i18n.pt_br import STRINGS as pt_br
        from src.i18n.pt_pt import STRINGS as pt_pt
        from src.i18n.de_de import STRINGS as de_de
        return {"en-US": en, "pt-BR": pt_br, "pt-PT": pt_pt, "de-DE": de_de}

    def test_pt_br_has_all_keys(self) -> None:
        catalogs = self._get_catalogs()
        missing = set(catalogs["en-US"].keys()) - set(catalogs["pt-BR"].keys())
        assert not missing, f"pt-BR missing keys: {sorted(missing)}"

    def test_pt_pt_has_all_keys(self) -> None:
        catalogs = self._get_catalogs()
        missing = set(catalogs["en-US"].keys()) - set(catalogs["pt-PT"].keys())
        assert not missing, f"pt-PT missing keys: {sorted(missing)}"

    def test_de_de_has_all_keys(self) -> None:
        catalogs = self._get_catalogs()
        missing = set(catalogs["en-US"].keys()) - set(catalogs["de-DE"].keys())
        assert not missing, f"de-DE missing keys: {sorted(missing)}"

    def test_no_extra_keys_in_pt_br(self) -> None:
        catalogs = self._get_catalogs()
        extra = set(catalogs["pt-BR"].keys()) - set(catalogs["en-US"].keys())
        assert not extra, f"pt-BR has extra keys: {sorted(extra)}"

    def test_no_extra_keys_in_pt_pt(self) -> None:
        catalogs = self._get_catalogs()
        extra = set(catalogs["pt-PT"].keys()) - set(catalogs["en-US"].keys())
        assert not extra, f"pt-PT has extra keys: {sorted(extra)}"

    def test_no_extra_keys_in_de_de(self) -> None:
        catalogs = self._get_catalogs()
        extra = set(catalogs["de-DE"].keys()) - set(catalogs["en-US"].keys())
        assert not extra, f"de-DE has extra keys: {sorted(extra)}"

    def test_all_locales_same_key_count(self) -> None:
        catalogs = self._get_catalogs()
        counts = {name: len(cat) for name, cat in catalogs.items()}
        assert len(set(counts.values())) == 1, f"Key counts differ: {counts}"

    def test_format_placeholders_match(self) -> None:
        """Verify that format placeholders in translations match the English reference."""
        catalogs = self._get_catalogs()
        en = catalogs["en-US"]
        placeholder_re = re.compile(r"\{(\w+)\}")

        errors: list[str] = []
        for locale_name in ("pt-BR", "pt-PT", "de-DE"):
            catalog = catalogs[locale_name]
            for key in en:
                en_placeholders = set(placeholder_re.findall(en[key]))
                tr_placeholders = set(placeholder_re.findall(catalog.get(key, "")))
                if en_placeholders != tr_placeholders:
                    errors.append(
                        f"{locale_name} key '{key}': "
                        f"expected {en_placeholders}, got {tr_placeholders}"
                    )

        assert not errors, "Placeholder mismatches:\n" + "\n".join(errors)

    def test_rich_markup_brackets_balanced(self) -> None:
        """Verify that Rich markup opening/closing tags are balanced."""
        catalogs = self._get_catalogs()
        tag_re = re.compile(r"\[/?[\w\s]+\]")

        errors: list[str] = []
        for locale_name, catalog in catalogs.items():
            for key, value in catalog.items():
                tags = tag_re.findall(value)
                # Count opening vs closing tags
                opening = [t for t in tags if not t.startswith("[/")]
                closing = [t for t in tags if t.startswith("[/")]
                if len(opening) != len(closing):
                    errors.append(
                        f"{locale_name} key '{key}': "
                        f"{len(opening)} opening vs {len(closing)} closing tags"
                    )

        assert not errors, "Unbalanced Rich markup:\n" + "\n".join(errors)


# ── Supported locales tests ────────────────────────────────────────────────


class TestSupportedLocales:
    """Verify the SUPPORTED_LOCALES constant."""

    def test_has_four_locales(self) -> None:
        from src.i18n import SUPPORTED_LOCALES
        assert len(SUPPORTED_LOCALES) == 4

    def test_default_locale_in_supported(self) -> None:
        from src.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES
        assert DEFAULT_LOCALE in SUPPORTED_LOCALES

    def test_all_locales_have_catalogs(self) -> None:
        from src.i18n import SUPPORTED_LOCALES, _load_catalog
        for locale in SUPPORTED_LOCALES:
            catalog = _load_catalog(locale)
            assert isinstance(catalog, dict)
            assert len(catalog) > 0
