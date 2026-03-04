"""Internationalization support for tenderx CLI.

Provides a simple dict-based translation system with lazy loading
and safe fallback to English (en-US).

Usage::

    from src.i18n import t, load_locale

    load_locale()                          # reads ~/.tenderx/config.json
    print(t("welcome.tagline"))
    print(t("ingest.done", fetched=10))    # format placeholders
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SUPPORTED_LOCALES: dict[str, str] = {
    "en-US": "English",
    "pt-BR": "Português do Brasil",
    "pt-PT": "Português de Portugal",
    "de-DE": "Deutsch",
}

DEFAULT_LOCALE = "en-US"
CONFIG_DIR = Path.home() / ".tenderx"
CONFIG_FILE = CONFIG_DIR / "config.json"

# ── Module-level state (lazy loaded) ──────────────────────────
_current_locale: str = DEFAULT_LOCALE
_catalog: dict[str, str] = {}
_fallback: dict[str, str] = {}
_loaded: bool = False


def _load_catalog(locale: str) -> dict[str, str]:
    """Import and return the translation dict for *locale*."""
    module_map = {
        "en-US": "src.i18n.en_us",
        "pt-BR": "src.i18n.pt_br",
        "pt-PT": "src.i18n.pt_pt",
        "de-DE": "src.i18n.de_de",
    }
    module_name = module_map.get(locale)
    if not module_name:
        logger.warning("Unknown locale %s, falling back to %s", locale, DEFAULT_LOCALE)
        module_name = module_map[DEFAULT_LOCALE]

    import importlib
    mod = importlib.import_module(module_name)
    return mod.STRINGS  # type: ignore[attr-defined]


def get_locale() -> str:
    """Return the current locale code (e.g. ``'pt-BR'``)."""
    return _current_locale


def set_locale(locale: str) -> None:
    """Set the active locale and load its catalog."""
    global _current_locale, _catalog, _fallback, _loaded
    if locale not in SUPPORTED_LOCALES:
        logger.warning("Unsupported locale: %s", locale)
        locale = DEFAULT_LOCALE
    _current_locale = locale
    _catalog = _load_catalog(locale)
    if locale != DEFAULT_LOCALE:
        _fallback = _load_catalog(DEFAULT_LOCALE)
    else:
        _fallback = _catalog
    _loaded = True


def load_locale() -> None:
    """Load locale from ``~/.tenderx/config.json``, or use default."""
    locale = DEFAULT_LOCALE
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            locale = data.get("locale", DEFAULT_LOCALE)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read config: %s", exc)
    set_locale(locale)


def save_locale(locale: str) -> None:
    """Persist locale choice to ``~/.tenderx/config.json``."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data["locale"] = locale
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def t(key: str, **kwargs: Any) -> str:
    """Translate *key*, formatting with *kwargs*.

    Lookup order: active locale → en-US fallback → raw key string.
    """
    global _loaded
    if not _loaded:
        load_locale()

    value = _catalog.get(key) or _fallback.get(key)
    if value is None:
        logger.warning("Missing translation key: %s (locale=%s)", key, _current_locale)
        return key  # return the key itself as last resort

    if kwargs:
        try:
            return value.format(**kwargs)
        except KeyError as exc:
            logger.warning("Format error for key %s: %s", key, exc)
            return value
    return value
