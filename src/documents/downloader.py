"""Download documents from tender supplier portals."""

import asyncio
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from src.db.models import Tender, TenderDocument
from src.db.session import get_session
from src.documents.storage import DocumentStorage

logger = logging.getLogger(__name__)

# Rate limit: 1 request per second
RATE_LIMIT_DELAY = 1.0

# Supported download extensions
DOWNLOAD_EXTENSIONS = {".pdf", ".zip", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".xml"}


@dataclass
class DownloadResult:
    """Result of a document download batch."""

    tenders_processed: int = 0
    documents_downloaded: int = 0
    documents_failed: int = 0
    total_bytes: int = 0
    errors: list[str] = field(default_factory=list)


class DocumentDownloader:
    """Download documents from supplier portals and store in MinIO."""

    def __init__(self, storage: DocumentStorage | None = None) -> None:
        self.storage = storage or DocumentStorage()

    async def download_for_supplier(
        self,
        domain: str,
        limit: int = 100,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> DownloadResult:
        """Download documents from tenders hosted on a specific supplier domain.

        Args:
            domain: The supplier domain to process.
            limit: Maximum tenders to process.
            on_progress: Optional callback(current, total) called after each tender.

        Returns:
            DownloadResult with counts and errors.
        """
        result = DownloadResult()

        await self.storage.ensure_bucket()

        async with get_session() as session:
            # Find tenders with document portal URLs matching the domain
            query_result = await session.execute(
                select(Tender)
                .where(
                    Tender.document_portal_url.isnot(None),
                    Tender.document_portal_url.contains(domain),
                )
                .limit(limit)
            )
            tenders = list(query_result.scalars().all())

        if not tenders:
            logger.info("No tenders found for domain: %s", domain)
            return result

        logger.info("Processing %d tenders from %s", len(tenders), domain)

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "GermanTendersBot/1.0"},
        ) as http_client:
            for tender in tenders:
                result.tenders_processed += 1
                try:
                    docs = await self._process_tender(
                        http_client, tender, result
                    )
                    await asyncio.sleep(RATE_LIMIT_DELAY)
                except Exception as exc:
                    result.errors.append(f"Tender {tender.id}: {exc}")
                    logger.warning("Error processing tender %s: %s", tender.id, exc)
                if on_progress:
                    on_progress(result.tenders_processed, len(tenders))

        return result

    async def _process_tender(
        self,
        http_client: httpx.AsyncClient,
        tender: Tender,
        result: DownloadResult,
    ) -> list[str]:
        """Scrape and download documents for a single tender."""
        url = tender.document_portal_url
        if not url:
            return []

        downloaded_keys: list[str] = []

        try:
            resp = await http_client.get(url)
            resp.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            result.documents_failed += 1
            result.errors.append(f"HTTP error fetching {url}: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        links = self._extract_document_links(soup, url)

        for doc_url, filename in links:
            try:
                doc_resp = await http_client.get(doc_url)
                doc_resp.raise_for_status()
                data = doc_resp.content

                content_type = doc_resp.headers.get("content-type", "application/octet-stream")
                storage_key = f"tenders/{tender.id}/{filename}"

                await self.storage.upload(storage_key, data, content_type)

                # Save to DB
                async with get_session() as session:
                    doc = TenderDocument(
                        tender_id=tender.id,
                        filename=filename,
                        content_type=content_type,
                        storage_key=storage_key,
                        storage_bucket=self.storage.bucket,
                        source_url=doc_url,
                        downloaded_at=datetime.now(timezone.utc),
                    )
                    session.add(doc)
                    await session.commit()

                result.documents_downloaded += 1
                result.total_bytes += len(data)
                downloaded_keys.append(storage_key)

                await asyncio.sleep(RATE_LIMIT_DELAY)

            except Exception as exc:
                result.documents_failed += 1
                result.errors.append(f"Failed to download {doc_url}: {exc}")
                logger.warning("Download error %s: %s", doc_url, exc)

        return downloaded_keys

    def _extract_document_links(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[tuple[str, str]]:
        """Extract downloadable document links from HTML.

        Returns:
            List of (url, filename) tuples.
        """
        from urllib.parse import urljoin

        links: list[tuple[str, str]] = []
        seen_urls: set[str] = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)

            if full_url in seen_urls:
                continue

            # Check if the link points to a downloadable file
            lower = href.lower()
            for ext in DOWNLOAD_EXTENSIONS:
                if lower.endswith(ext) or ext in lower:
                    filename = self._extract_filename(href, ext)
                    links.append((full_url, filename))
                    seen_urls.add(full_url)
                    break

        return links

    def _extract_filename(self, href: str, ext: str) -> str:
        """Extract a filename from a URL."""
        # Try to get filename from URL path
        parts = href.rstrip("/").split("/")
        for part in reversed(parts):
            if ext in part.lower():
                # Clean query params
                clean = part.split("?")[0].split("#")[0]
                if clean:
                    return clean

        return f"document{ext}"
