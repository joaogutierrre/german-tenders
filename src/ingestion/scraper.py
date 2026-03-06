"""UI scraping fallback for fields not available via the bulk export API.

The oeffentlichevergabe.de API exports (CSV + OCDS) cover most required
fields, but some — notably ``eu_funded`` and ``award_criteria`` details —
are only visible on the web UI.  This module provides best-effort scraping
of the tender detail page to fill those gaps.

**Usage**::

    from src.ingestion.scraper import TenderDetailScraper

    scraper = TenderDetailScraper()
    extra = await scraper.scrape_detail(notice_id="ABC-123")
    # extra.eu_funded -> True / False / None
    # extra.award_criteria -> dict | None

**Limitations:**
- The platform is JavaScript-heavy; static HTML scraping can miss
  dynamically loaded sections.  For full fidelity, use a headless browser
  (Playwright) — but that adds complexity and is not justified for the MVP.
- Rate-limited to 1 request/second to avoid IP blocking.
- Results are cached per-session to avoid redundant fetches.

See ``docs/data_gaps.md`` for a detailed analysis of which fields are
available, which are missing, and why scraping is limited.
"""

import asyncio
import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.oeffentlichevergabe.de"

# EU-funding related keywords (German and English)
_EU_KEYWORDS = [
    "eu-finanziert",
    "eu-mittel",
    "eu-foerderung",
    "eu-funded",
    "efre",
    "esf",
    "horizon europe",
    "horizon 2020",
    "europaeisch",
    "europaeische union",
    "kohäsionsfonds",
    "cohesion fund",
    "strukturfonds",
    "structural fund",
]

# Renewal/framework agreement keywords
_RENEWAL_KEYWORDS = [
    "verlängerungsoption",
    "verlaengerungsoption",
    "verlängerung",
    "verlaengerung",
    "rahmenvereinbarung",
    "framework agreement",
    "renewable",
    "optional renewal",
    "optionale verlängerung",
    "verlängerbar",
    "verlaengerbar",
]


@dataclass
class ScrapedTenderDetail:
    """Extra fields scraped from the tender detail page."""

    notice_id: str
    eu_funded: bool | None = None
    award_criteria: dict | None = None
    raw_html_snippet: str | None = None
    scraped: bool = False
    error: str | None = None


@dataclass
class ScrapeResult:
    """Aggregate result of a scraping batch run."""

    total: int = 0
    scraped: int = 0
    eu_funded_found: int = 0
    criteria_found: int = 0
    errors: int = 0
    skipped_rate_limit: int = 0


class TenderDetailScraper:
    """Best-effort scraper for tender detail pages.

    Fetches the oeffentlichevergabe.de detail page for a notice and
    attempts to extract fields not available in the bulk API exports.

    Attributes:
        base_url: Platform base URL.
        delay: Seconds between requests (rate limiting).
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        delay: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url
        self.delay = delay
        self.timeout = timeout
        self._cache: dict[str, ScrapedTenderDetail] = {}

    async def scrape_detail(
        self, notice_id: str
    ) -> ScrapedTenderDetail:
        """Scrape the tender detail page for a single notice.

        Args:
            notice_id: The notice identifier (e.g., ``"ABC-123"``).

        Returns:
            ScrapedTenderDetail with any extra fields found.
        """
        if notice_id in self._cache:
            return self._cache[notice_id]

        detail_url = (
            f"{self.base_url}/ui/de/search/details/{notice_id}"
        )
        result = ScrapedTenderDetail(notice_id=notice_id)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    detail_url,
                    follow_redirects=True,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (compatible; TenderX/1.0; "
                            "+https://github.com/joaogutierrre/german-tenders)"
                        ),
                        "Accept": "text/html",
                        "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
                    },
                )

            if resp.status_code != 200:
                result.error = f"HTTP {resp.status_code}"
                logger.debug(
                    "Scrape failed for %s: HTTP %d",
                    notice_id,
                    resp.status_code,
                )
                self._cache[notice_id] = result
                return result

            html = resp.text
            result.scraped = True

            # Attempt EU-funding detection from HTML text
            result.eu_funded = self._detect_eu_funded(html)

            # Attempt award criteria extraction
            result.award_criteria = self._extract_award_criteria(html)

            # Store a snippet for debugging
            if len(html) > 500:
                result.raw_html_snippet = html[:500]

        except httpx.TimeoutException:
            result.error = "timeout"
            logger.debug("Scrape timeout for %s", notice_id)
        except httpx.HTTPError as exc:
            result.error = str(exc)
            logger.debug("Scrape error for %s: %s", notice_id, exc)

        self._cache[notice_id] = result
        return result

    async def scrape_batch(
        self,
        notice_ids: list[str],
        max_count: int | None = None,
    ) -> tuple[list[ScrapedTenderDetail], ScrapeResult]:
        """Scrape multiple tender detail pages with rate limiting.

        Args:
            notice_ids: List of notice identifiers to scrape.
            max_count: Maximum number of pages to scrape (for testing).

        Returns:
            Tuple of (list of details, aggregate ScrapeResult).
        """
        ids = notice_ids[:max_count] if max_count else notice_ids
        result = ScrapeResult(total=len(ids))
        details: list[ScrapedTenderDetail] = []

        for i, nid in enumerate(ids):
            if i > 0:
                await asyncio.sleep(self.delay)

            detail = await self.scrape_detail(nid)
            details.append(detail)

            if detail.scraped:
                result.scraped += 1
                if detail.eu_funded is not None:
                    result.eu_funded_found += 1
                if detail.award_criteria:
                    result.criteria_found += 1
            elif detail.error:
                result.errors += 1

        logger.info(
            "Scrape batch: %d/%d scraped, %d EU-funded found, %d criteria found, %d errors",
            result.scraped,
            result.total,
            result.eu_funded_found,
            result.criteria_found,
            result.errors,
        )
        return details, result

    @staticmethod
    def _detect_eu_funded(html: str) -> bool | None:
        """Check HTML text for EU-funding indicators.

        Uses keyword matching on the raw HTML.  This is a heuristic —
        the platform may display EU-funding info in various formats.

        Args:
            html: Raw HTML text of the detail page.

        Returns:
            True if EU-funding keywords are found, None if inconclusive.
        """
        html_lower = html.lower()
        for keyword in _EU_KEYWORDS:
            if keyword in html_lower:
                return True
        return None

    @staticmethod
    def _extract_award_criteria(html: str) -> dict | None:
        """Attempt to extract award criteria from HTML.

        Looks for common patterns in the detail page indicating
        price/quality weighting.

        Args:
            html: Raw HTML text of the detail page.

        Returns:
            Dict with criteria info, or None if not found.

        Note:
            This is best-effort.  The platform renders criteria in
            various formats (tables, lists, plain text).  Full
            extraction would require a headless browser + CSS selectors
            for each layout variant.
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Look for criteria section by common headings
            criteria_headings = [
                "zuschlagskriterien",
                "award criteria",
                "bewertungskriterien",
                "wertungskriterien",
            ]

            for heading_text in criteria_headings:
                # Find elements containing the heading text
                for element in soup.find_all(
                    ["h1", "h2", "h3", "h4", "h5", "h6", "th", "dt", "strong", "b"]
                ):
                    if heading_text in (element.get_text() or "").lower():
                        # Get the next sibling or parent's text for criteria details
                        parent = element.parent
                        if parent:
                            text = parent.get_text(separator="\n", strip=True)
                            return {
                                "raw_text": text[:500],
                                "source": "scraped",
                            }

        except ImportError:
            logger.debug("BeautifulSoup not available for criteria extraction")
        except Exception as exc:
            logger.debug("Criteria extraction failed: %s", exc)

        return None
