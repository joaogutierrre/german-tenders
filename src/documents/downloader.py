"""Download documents from tender supplier portals."""

import asyncio
import inspect
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

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
DOWNLOAD_EXTENSIONS = {
    ".pdf", ".zip", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".xml",
}

# Content types that indicate a downloadable file (not HTML)
FILE_CONTENT_TYPES = {
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "text/xml",
    "application/xml",
    "application/octet-stream",
}

# Query params that suggest a download link
DOWNLOAD_QUERY_PATTERNS = re.compile(
    r"action=download|download=true|type=download|mode=download"
    r"|do=download|cmd=download|op=download",
    re.IGNORECASE,
)


@dataclass
class DownloadResult:
    """Result of a document download batch."""

    tenders_processed: int = 0
    documents_downloaded: int = 0
    documents_failed: int = 0
    tenders_no_links: int = 0
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

        # Emit initial progress so dashboard shows total immediately
        if on_progress:
            ret = on_progress(0, len(tenders))
            if inspect.isawaitable(ret):
                await ret

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
                    ret = on_progress(result.tenders_processed, len(tenders))
                    if inspect.isawaitable(ret):
                        await ret

        logger.info(
            "Download complete: %d tenders, %d docs downloaded, "
            "%d failed, %d no links, %d bytes",
            result.tenders_processed,
            result.documents_downloaded,
            result.documents_failed,
            result.tenders_no_links,
            result.total_bytes,
        )
        return result

    async def _process_tender(
        self,
        http_client: httpx.AsyncClient,
        tender: Tender,
        result: DownloadResult,
    ) -> list[str]:
        """Scrape and download documents for a single tender.

        Strategy:
        1. Try direct download (HEAD → Content-Type check)
        2. If HTML, try portal-specific handlers
        3. Fall back to generic HTML scraping (enhanced)
        """
        url = tender.document_portal_url
        if not url:
            return []

        downloaded_keys: list[str] = []

        # ── Step 1: Try direct download (non-HTML response) ──
        direct = await self._try_direct_download(http_client, url, tender, result)
        if direct:
            return direct

        # ── Step 2: Fetch HTML and scrape ──
        try:
            resp = await http_client.get(url)
            resp.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            result.documents_failed += 1
            result.errors.append(f"HTTP error fetching {url}: {exc}")
            return []

        content_type = resp.headers.get("content-type", "")
        if not content_type.startswith("text/html"):
            # Non-HTML response that wasn't caught by HEAD — try saving directly
            keys = await self._save_direct_response(resp, tender, result)
            if keys:
                return keys

        soup = BeautifulSoup(resp.text, "html.parser")

        # ── Step 2a: Try portal-specific handlers ──
        portal_links = self._get_portal_specific_links(soup, url)

        # ── Step 2b: Enhanced generic link extraction ──
        generic_links = self._extract_document_links(soup, url)

        # Merge, dedup
        all_links = portal_links + generic_links
        seen: set[str] = set()
        unique_links: list[tuple[str, str]] = []
        for doc_url, filename in all_links:
            if doc_url not in seen:
                unique_links.append((doc_url, filename))
                seen.add(doc_url)

        if not unique_links:
            result.tenders_no_links += 1
            a_tags = soup.find_all("a", href=True)
            logger.info(
                "No document links found for tender %s (%s). "
                "Page has %d <a> tags, final URL: %s",
                tender.id, url, len(a_tags), resp.url,
            )
            return []

        # ── Step 3: Download each linked file ──
        for doc_url, filename in unique_links:
            key = await self._download_and_store(
                http_client, doc_url, filename, tender, result
            )
            if key:
                downloaded_keys.append(key)

        return downloaded_keys

    # ── Direct download detection ─────────────────────────────

    async def _try_direct_download(
        self,
        http_client: httpx.AsyncClient,
        url: str,
        tender: Tender,
        result: DownloadResult,
    ) -> list[str] | None:
        """HEAD request to check if URL points to a file (not HTML).

        Returns list of storage keys if successful, None otherwise.
        """
        try:
            head_resp = await http_client.head(url, follow_redirects=True)
            content_type = head_resp.headers.get("content-type", "")
            content_disp = head_resp.headers.get("content-disposition", "")

            base_type = content_type.split(";")[0].strip().lower()

            if base_type in FILE_CONTENT_TYPES or content_disp:
                # This is a file, download it directly
                resp = await http_client.get(url)
                resp.raise_for_status()
                return await self._save_direct_response(resp, tender, result)
        except (httpx.HTTPError, httpx.TimeoutException):
            pass  # Fall through to HTML scraping
        return None

    async def _save_direct_response(
        self,
        resp: httpx.Response,
        tender: Tender,
        result: DownloadResult,
    ) -> list[str]:
        """Save a direct (non-HTML) HTTP response as a document."""
        content_type = resp.headers.get("content-type", "application/octet-stream")
        base_type = content_type.split(";")[0].strip().lower()

        # Skip if it's still HTML
        if base_type.startswith("text/html"):
            return []

        filename = self._extract_filename_from_response(resp)
        data = resp.content

        if not data:
            return []

        storage_key = f"tenders/{tender.id}/{filename}"
        try:
            await self.storage.upload(storage_key, data, content_type)

            async with get_session() as session:
                doc = TenderDocument(
                    tender_id=tender.id,
                    filename=filename,
                    content_type=content_type,
                    storage_key=storage_key,
                    storage_bucket=self.storage.bucket,
                    source_url=str(resp.url),
                    downloaded_at=datetime.now(timezone.utc),
                )
                session.add(doc)
                await session.commit()

            result.documents_downloaded += 1
            result.total_bytes += len(data)
            logger.info(
                "Direct download: %s (%d bytes) for tender %s",
                filename, len(data), tender.id,
            )
            return [storage_key]
        except Exception as exc:
            result.documents_failed += 1
            result.errors.append(f"Failed to store direct download {resp.url}: {exc}")
            logger.warning("Direct download store error: %s", exc)
            return []

    # ── Download and store a single document ──────────────────

    async def _download_and_store(
        self,
        http_client: httpx.AsyncClient,
        doc_url: str,
        filename: str,
        tender: Tender,
        result: DownloadResult,
    ) -> str | None:
        """Download a single document URL and store in MinIO + DB.

        Returns storage key if successful, None otherwise.
        """
        try:
            doc_resp = await http_client.get(doc_url)
            doc_resp.raise_for_status()
            data = doc_resp.content

            if not data:
                return None

            # Check if the response is actually HTML (not a file)
            resp_type = doc_resp.headers.get("content-type", "")
            base_resp_type = resp_type.split(";")[0].strip().lower()
            if base_resp_type.startswith("text/html") and len(data) < 50_000:
                # Likely an error page or redirect, not a real document
                logger.debug("Skipping HTML response for %s", doc_url)
                return None

            content_type = resp_type or "application/octet-stream"
            # Try to get a better filename from the response
            resp_filename = self._extract_filename_from_response(doc_resp)
            if resp_filename != "document.bin":
                filename = resp_filename

            storage_key = f"tenders/{tender.id}/{filename}"

            await self.storage.upload(storage_key, data, content_type)

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

            await asyncio.sleep(RATE_LIMIT_DELAY)
            return storage_key

        except Exception as exc:
            result.documents_failed += 1
            result.errors.append(f"Failed to download {doc_url}: {exc}")
            logger.warning("Download error %s: %s", doc_url, exc)
            return None

    # ── Portal-specific handlers ──────────────────────────────

    def _get_portal_specific_links(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[tuple[str, str]]:
        """Try portal-specific extraction patterns.

        Returns list of (url, filename) tuples.
        """
        parsed = urlparse(base_url)
        domain = parsed.hostname or ""

        links: list[tuple[str, str]] = []

        if "deutsche-evergabe.de" in domain:
            links = self._portal_deutsche_evergabe(soup, base_url)
        elif "subreport.de" in domain:
            links = self._portal_subreport(soup, base_url)
        elif "dtvp.de" in domain:
            links = self._portal_dtvp(soup, base_url)
        elif "vergabe.aumass" in domain or "aumass.de" in domain:
            links = self._portal_aumass(soup, base_url)

        return links

    def _portal_deutsche_evergabe(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[tuple[str, str]]:
        """Handle deutsche-evergabe.de portals.

        Known patterns:
        - Links with /dashboards/dashboard_off/ paths
        - Download buttons with data-* attributes
        - File links in document tables
        """
        links: list[tuple[str, str]] = []

        # Look for download links in common class patterns
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)

            # Links to files within the dashboard
            if "/download" in href.lower() or "/file" in href.lower():
                filename = self._extract_filename(href, ".pdf")
                links.append((full_url, filename))

            # Links with download class or data-download attribute
            classes = a_tag.get("class", [])
            if isinstance(classes, list):
                class_str = " ".join(classes).lower()
            else:
                class_str = str(classes).lower()

            if "download" in class_str or a_tag.get("download"):
                filename = a_tag.get("download") or self._extract_filename(href, ".pdf")
                links.append((full_url, filename))

        return links

    def _portal_subreport(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[tuple[str, str]]:
        """Handle subreport.de portal — document listing pages."""
        links: list[tuple[str, str]] = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)

            if "/document" in href.lower() or "/download" in href.lower():
                filename = self._extract_filename(href, ".pdf")
                links.append((full_url, filename))

        return links

    def _portal_dtvp(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[tuple[str, str]]:
        """Handle dtvp.de portal — Deutsches Vergabeportal."""
        links: list[tuple[str, str]] = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)

            if "/download" in href.lower() or "document" in href.lower():
                filename = self._extract_filename(href, ".pdf")
                links.append((full_url, filename))

        return links

    def _portal_aumass(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[tuple[str, str]]:
        """Handle aumass.de portal — construction tender platform."""
        links: list[tuple[str, str]] = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)

            if any(kw in href.lower() for kw in ("/download", "/document", "/file")):
                filename = self._extract_filename(href, ".pdf")
                links.append((full_url, filename))

        return links

    # ── Enhanced generic link extraction ──────────────────────

    def _extract_document_links(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[tuple[str, str]]:
        """Extract downloadable document links from HTML.

        Uses 5 strategies:
        1. <a> tags with file extension hrefs (original)
        2. <a download="..."> attribute detection
        3. Links with download-like query parameters
        4. <iframe src="document.pdf"> detection
        5. <meta http-equiv="refresh"> redirect detection

        Returns:
            List of (url, filename) tuples.
        """
        links: list[tuple[str, str]] = []
        seen_urls: set[str] = set()

        def _add(url: str, fname: str) -> None:
            if url not in seen_urls:
                links.append((url, fname))
                seen_urls.add(url)

        # Strategy 1: <a> tags with file extension hrefs
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)

            lower = href.lower()
            for ext in DOWNLOAD_EXTENSIONS:
                if lower.endswith(ext) or ext in lower:
                    filename = self._extract_filename(href, ext)
                    _add(full_url, filename)
                    break

        # Strategy 2: <a download="..."> attribute
        for a_tag in soup.find_all("a", download=True):
            href = a_tag.get("href", "")
            if not href:
                continue
            full_url = urljoin(base_url, href)
            download_attr = a_tag["download"]
            filename = download_attr if download_attr else "document.bin"
            _add(full_url, filename)

        # Strategy 3: Links with download-like query parameters
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if DOWNLOAD_QUERY_PATTERNS.search(href):
                full_url = urljoin(base_url, href)
                filename = self._extract_filename(href, ".pdf")
                _add(full_url, filename)

        # Strategy 4: <iframe> sources pointing to documents
        for iframe in soup.find_all("iframe", src=True):
            src = iframe["src"]
            lower_src = src.lower()
            for ext in DOWNLOAD_EXTENSIONS:
                if ext in lower_src:
                    full_url = urljoin(base_url, src)
                    filename = self._extract_filename(src, ext)
                    _add(full_url, filename)
                    break

        # Strategy 5: <meta http-equiv="refresh"> redirect
        for meta in soup.find_all("meta", attrs={"http-equiv": "refresh"}):
            content = meta.get("content", "")
            match = re.search(r"url\s*=\s*(.+)", content, re.IGNORECASE)
            if match:
                redirect_url = match.group(1).strip().strip("'\"")
                lower_redir = redirect_url.lower()
                for ext in DOWNLOAD_EXTENSIONS:
                    if ext in lower_redir:
                        full_url = urljoin(base_url, redirect_url)
                        filename = self._extract_filename(redirect_url, ext)
                        _add(full_url, filename)
                        break

        return links

    # ── Filename utilities ────────────────────────────────────

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

    def _extract_filename_from_response(self, resp: httpx.Response) -> str:
        """Extract filename from HTTP response headers or URL.

        Checks Content-Disposition header first, then falls back to URL path.
        """
        # Try Content-Disposition header
        content_disp = resp.headers.get("content-disposition", "")
        if content_disp:
            # RFC 6266: attachment; filename="report.pdf"
            match = re.search(
                r'filename\*?=["\']?(?:UTF-8\'\')?([^"\';\s]+)', content_disp
            )
            if match:
                return match.group(1)

        # Try URL path
        path = urlparse(str(resp.url)).path
        if path and path != "/":
            last_segment = path.rstrip("/").split("/")[-1]
            clean = last_segment.split("?")[0].split("#")[0]
            if clean and "." in clean:
                return clean

        # Guess extension from Content-Type
        content_type = resp.headers.get("content-type", "")
        base_type = content_type.split(";")[0].strip().lower()
        ext_map = {
            "application/pdf": ".pdf",
            "application/zip": ".zip",
            "application/x-zip-compressed": ".zip",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.ms-excel": ".xls",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "text/csv": ".csv",
            "text/xml": ".xml",
            "application/xml": ".xml",
        }
        ext = ext_map.get(base_type, ".bin")
        return f"document{ext}"
