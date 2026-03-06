"""Extract document URLs from OCDS ZIP exports and enrich tenders."""

import io
import json
import logging
import zipfile
from dataclasses import dataclass

from sqlalchemy import select, update

from src.db.models import Tender
from src.db.session import get_session

logger = logging.getLogger(__name__)


@dataclass
class OCDSEnrichResult:
    """Result of OCDS document URL enrichment."""

    notices_in_ocds: int = 0
    urls_found: int = 0
    tenders_updated: int = 0
    tenders_not_found: int = 0
    errors: int = 0


def parse_ocds_zip(zip_bytes: bytes) -> dict[str, list[str]]:
    """Parse an OCDS ZIP export and extract document URLs per notice.

    The OCDS ZIP contains one or more JSON files. Each JSON has a
    ``releases`` array where each release may contain
    ``tender.documents[]`` with ``url`` fields.

    Args:
        zip_bytes: Raw OCDS ZIP file content.

    Returns:
        Dict mapping notice_id to a deduplicated list of document URLs.
    """
    if not zip_bytes:
        return {}

    result: dict[str, list[str]] = {}

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        logger.warning("Invalid ZIP file for OCDS export")
        return {}

    for name in zf.namelist():
        if not name.endswith(".json"):
            continue

        try:
            raw = zf.read(name)
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("Failed to parse %s in OCDS ZIP: %s", name, exc)
            continue

        # Handle both single-release and multi-release structures
        releases = data.get("releases", [])
        if not isinstance(releases, list):
            # Single release envelope (per-notice endpoint)
            releases = [data] if "tender" in data else []

        for release in releases:
            notice_id = _extract_notice_id(release)
            if not notice_id:
                continue

            tender_obj = release.get("tender", {})
            documents = tender_obj.get("documents", [])
            if not isinstance(documents, list):
                continue

            urls: list[str] = []
            seen: set[str] = set()
            for doc in documents:
                url = doc.get("url", "").strip()
                if url and url not in seen:
                    urls.append(url)
                    seen.add(url)

            if urls:
                # Merge with existing entries for this notice
                existing = result.get(notice_id, [])
                existing_set = set(existing)
                for u in urls:
                    if u not in existing_set:
                        existing.append(u)
                        existing_set.add(u)
                result[notice_id] = existing

    logger.info(
        "Parsed OCDS ZIP: %d notices with document URLs (%d total URLs)",
        len(result),
        sum(len(v) for v in result.values()),
    )
    return result


def _extract_notice_id(release: dict) -> str | None:
    """Extract the notice identifier from an OCDS release.

    Tries multiple paths: release.id, release.tender.id, or parsing
    the ocid field.

    Args:
        release: An OCDS release object.

    Returns:
        The notice identifier string, or None.
    """
    # Direct release id (most common in bulk exports)
    release_id = release.get("id", "")
    if release_id:
        return str(release_id)

    # From tender.id
    tender_id = release.get("tender", {}).get("id", "")
    if tender_id:
        return str(tender_id)

    # Parse from ocid (format: "ocds-prefix-{notice_id}")
    ocid = release.get("ocid", "")
    if ocid:
        parts = ocid.split("-", 2)
        if len(parts) >= 3:
            return parts[2]

    return None


async def enrich_document_urls(
    ocds_data: dict[str, list[str]],
) -> OCDSEnrichResult:
    """Update tenders' document_portal_url from OCDS document data.

    For each notice ID in the OCDS data, find the matching tender in the
    database and update its ``document_portal_url`` with the first
    tender-specific URL from OCDS. Only updates if the existing URL is
    NULL or appears to be a generic issuer website.

    Args:
        ocds_data: Dict mapping notice_id to list of document URLs
                   (from ``parse_ocds_zip``).

    Returns:
        OCDSEnrichResult with counts.
    """
    result = OCDSEnrichResult(
        notices_in_ocds=len(ocds_data),
        urls_found=sum(len(v) for v in ocds_data.values()),
    )

    if not ocds_data:
        return result

    async with get_session() as session:
        for notice_id, urls in ocds_data.items():
            try:
                best_url = urls[0] if urls else None
                if not best_url:
                    continue

                # Match by source_id prefix (source_id = "{notice_id}-{version}")
                query = select(Tender).where(
                    Tender.source_id.startswith(notice_id)
                )
                db_result = await session.execute(query)
                tenders = list(db_result.scalars().all())

                if not tenders:
                    result.tenders_not_found += 1
                    continue

                for tender in tenders:
                    current_url = tender.document_portal_url
                    if _should_update_url(current_url, best_url):
                        tender.document_portal_url = best_url
                        result.tenders_updated += 1

            except Exception as exc:
                result.errors += 1
                logger.warning(
                    "Error enriching notice %s: %s", notice_id, exc
                )

        await session.commit()

    logger.info(
        "OCDS enrichment: %d updated, %d not found, %d errors",
        result.tenders_updated,
        result.tenders_not_found,
        result.errors,
    )
    return result


def _should_update_url(current_url: str | None, ocds_url: str) -> bool:
    """Determine if the current URL should be replaced with the OCDS URL.

    Updates when:
    - Current URL is None/empty
    - Current URL looks like a generic issuer website (no path UUID or ID)
    - OCDS URL contains a path with UUID-like or notice-specific segments

    Args:
        current_url: The tender's existing document_portal_url.
        ocds_url: The URL from OCDS documents.

    Returns:
        True if the OCDS URL is a better choice.
    """
    if not current_url or not current_url.strip():
        return True

    # If URLs are the same, no update needed
    if current_url.strip().rstrip("/") == ocds_url.strip().rstrip("/"):
        return False

    from urllib.parse import urlparse

    current_parsed = urlparse(current_url)
    ocds_parsed = urlparse(ocds_url)

    # If current URL has a very short path (just "/" or empty), OCDS is better
    current_path = current_parsed.path.strip("/")
    if not current_path or len(current_path) < 5:
        return True

    # If OCDS URL has a longer, more specific path, prefer it
    ocds_path = ocds_parsed.path.strip("/")
    if len(ocds_path) > len(current_path):
        return True

    return False
