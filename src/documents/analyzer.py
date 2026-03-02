"""Analyze document hosting suppliers from tender portal URLs."""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select

from src.db.models import Tender
from src.db.session import get_session

logger = logging.getLogger(__name__)


@dataclass
class SupplierStats:
    """Statistics for a document supplier domain."""

    domain: str
    tender_count: int
    percentage: float
    sample_urls: list[str]


class SupplierAnalyzer:
    """Analyze document_portal_url to identify top document suppliers."""

    async def analyze(self) -> list[SupplierStats]:
        """Group tenders by document portal domain.

        Returns:
            List of SupplierStats sorted by tender_count descending.
        """
        domain_map: dict[str, list[str]] = {}

        async with get_session() as session:
            result = await session.execute(
                select(Tender.document_portal_url).where(
                    Tender.document_portal_url.isnot(None),
                    Tender.document_portal_url != "",
                )
            )
            urls = [row[0] for row in result.fetchall()]

        if not urls:
            return []

        total = len(urls)

        for url in urls:
            domain = extract_domain(url)
            if domain:
                domain_map.setdefault(domain, []).append(url)

        stats = [
            SupplierStats(
                domain=domain,
                tender_count=len(url_list),
                percentage=len(url_list) / total * 100,
                sample_urls=url_list[:3],
            )
            for domain, url_list in domain_map.items()
        ]

        stats.sort(key=lambda s: s.tender_count, reverse=True)
        return stats

    def export_csv(self, stats: list[SupplierStats], path: Path) -> None:
        """Export supplier statistics to CSV."""
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["domain", "tender_count", "percentage", "sample_url"])
            for s in stats:
                writer.writerow([
                    s.domain,
                    s.tender_count,
                    f"{s.percentage:.1f}",
                    s.sample_urls[0] if s.sample_urls else "",
                ])

        logger.info("Exported %d suppliers to %s", len(stats), path)


def extract_domain(url: str) -> str | None:
    """Extract the base domain from a URL."""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urlparse(url)
        return parsed.netloc.lower() if parsed.netloc else None
    except Exception:
        return None
