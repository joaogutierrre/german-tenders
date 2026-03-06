"""Tests for the UI scraping fallback module."""

import pytest

from src.ingestion.scraper import (
    ScrapedTenderDetail,
    ScrapeResult,
    TenderDetailScraper,
    _EU_KEYWORDS,
    _RENEWAL_KEYWORDS,
)


class TestEUFundedDetection:
    """Test EU-funding keyword detection in HTML."""

    def test_detects_eu_finanziert(self):
        html = '<div class="badge">EU-finanziert</div>'
        result = TenderDetailScraper._detect_eu_funded(html)
        assert result is True

    def test_detects_efre(self):
        html = "<p>Dieses Projekt wird aus EFRE-Mitteln finanziert.</p>"
        result = TenderDetailScraper._detect_eu_funded(html)
        assert result is True

    def test_detects_horizon_europe(self):
        html = "<p>Funded under Horizon Europe programme.</p>"
        result = TenderDetailScraper._detect_eu_funded(html)
        assert result is True

    def test_detects_esf(self):
        html = "<span>ESF-Foerderung</span>"
        result = TenderDetailScraper._detect_eu_funded(html)
        assert result is True

    def test_returns_none_when_no_keywords(self):
        html = "<p>Bundesautobahn Sanierung Abschnitt 3</p>"
        result = TenderDetailScraper._detect_eu_funded(html)
        assert result is None

    def test_case_insensitive(self):
        html = "<p>EU-FINANZIERT project</p>"
        result = TenderDetailScraper._detect_eu_funded(html)
        assert result is True

    def test_empty_html(self):
        result = TenderDetailScraper._detect_eu_funded("")
        assert result is None


class TestAwardCriteriaExtraction:
    """Test award criteria extraction from HTML."""

    def test_extracts_criteria_from_heading(self):
        html = """
        <div>
            <h3>Zuschlagskriterien</h3>
            <p>Preis: 60%, Qualitaet: 40%</p>
        </div>
        """
        result = TenderDetailScraper._extract_award_criteria(html)
        assert result is not None
        assert "raw_text" in result
        assert "source" in result
        assert result["source"] == "scraped"
        assert "Preis" in result["raw_text"]

    def test_extracts_from_strong_tag(self):
        html = """
        <div>
            <strong>Zuschlagskriterien</strong>
            <span>Wirtschaftlichkeit des Angebots</span>
        </div>
        """
        result = TenderDetailScraper._extract_award_criteria(html)
        assert result is not None

    def test_returns_none_when_no_criteria(self):
        html = "<p>This tender has no criteria information.</p>"
        result = TenderDetailScraper._extract_award_criteria(html)
        assert result is None

    def test_truncates_long_text(self):
        criteria_text = "Preis " * 200  # Very long criteria text
        html = f"""
        <div>
            <h3>Zuschlagskriterien</h3>
            <p>{criteria_text}</p>
        </div>
        """
        result = TenderDetailScraper._extract_award_criteria(html)
        assert result is not None
        assert len(result["raw_text"]) <= 500


class TestScrapedTenderDetail:
    """Test ScrapedTenderDetail dataclass."""

    def test_default_values(self):
        detail = ScrapedTenderDetail(notice_id="TEST-001")
        assert detail.notice_id == "TEST-001"
        assert detail.eu_funded is None
        assert detail.award_criteria is None
        assert detail.scraped is False
        assert detail.error is None

    def test_with_values(self):
        detail = ScrapedTenderDetail(
            notice_id="TEST-002",
            eu_funded=True,
            award_criteria={"raw_text": "Preis: 100%", "source": "scraped"},
            scraped=True,
        )
        assert detail.eu_funded is True
        assert detail.award_criteria is not None


class TestScrapeResult:
    """Test ScrapeResult dataclass."""

    def test_default_values(self):
        result = ScrapeResult()
        assert result.total == 0
        assert result.scraped == 0
        assert result.eu_funded_found == 0
        assert result.criteria_found == 0
        assert result.errors == 0

    def test_with_values(self):
        result = ScrapeResult(
            total=10,
            scraped=8,
            eu_funded_found=3,
            criteria_found=5,
            errors=2,
        )
        assert result.total == 10
        assert result.scraped == 8


class TestKeywordLists:
    """Verify keyword lists are non-empty and contain expected terms."""

    def test_eu_keywords_not_empty(self):
        assert len(_EU_KEYWORDS) > 0

    def test_eu_keywords_contains_core_terms(self):
        assert "eu-finanziert" in _EU_KEYWORDS
        assert "efre" in _EU_KEYWORDS
        assert "esf" in _EU_KEYWORDS

    def test_renewal_keywords_not_empty(self):
        assert len(_RENEWAL_KEYWORDS) > 0

    def test_renewal_keywords_contains_core_terms(self):
        assert "rahmenvereinbarung" in _RENEWAL_KEYWORDS
        assert "framework agreement" in _RENEWAL_KEYWORDS


class TestTenderDetailScraper:
    """Test TenderDetailScraper initialization and caching."""

    def test_default_config(self):
        scraper = TenderDetailScraper()
        assert scraper.delay == 1.0
        assert scraper.timeout == 30.0

    def test_custom_config(self):
        scraper = TenderDetailScraper(delay=2.0, timeout=60.0)
        assert scraper.delay == 2.0
        assert scraper.timeout == 60.0

    def test_cache_starts_empty(self):
        scraper = TenderDetailScraper()
        assert len(scraper._cache) == 0
