"""Load organizations from CSV files."""

import csv
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.db.repositories import OrganizationRepository
from src.db.session import get_session

logger = logging.getLogger(__name__)

TAX_ID_PATTERN = re.compile(r"^DE\d{9}$")

# Column name mappings: real CSV header → internal key
_COLUMN_ALIASES: dict[str, str] = {
    # Standard format
    "tax_id": "tax_id",
    "name": "name",
    "website": "website",
    # Real challenge CSV format
    "organisationidentifier": "tax_id",
    "organisationname": "name",
    "organisationinternetaddress": "website",
    "organisationcity": "city",
    "organisationpostcode": "postcode",
    "organisationcountrysubdivision": "nuts_code",
    "organisationcountrycode": "country",
    "winnersize": "size",
    "organisationrole": "role",
}


@dataclass
class LoadResult:
    """Result of a CSV load operation."""

    total_rows: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _normalize_website(url: str | None) -> str | None:
    """Normalize a website URL."""
    if not url or not url.strip():
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _detect_delimiter(sample: str) -> str:
    """Auto-detect CSV delimiter from a sample line."""
    for delim in [";", ",", "\t"]:
        if delim in sample:
            return delim
    return ","


def _extract_de_tax_id(raw: str) -> str | None:
    """Extract a DE+9digit tax ID from a potentially messy identifier.

    Handles formats like:
      - 'DE123456789'
      - 'DE 123 456 789'
      - 'DE 124 469 636-00001'
      - 'UStID. DE 130487158'
      - 'Steuernummer: DE 296 970 953'
    """
    if not raw or not raw.strip():
        return None
    # Remove all spaces and search for DE + 9 digits
    cleaned = raw.replace(" ", "")
    match = re.search(r"DE(\d{9})", cleaned)
    if match:
        return "DE" + match.group(1)
    return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file with encoding and delimiter auto-detection."""
    raw: bytes = path.read_bytes()

    # Try encodings
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Cannot decode {path} with any supported encoding")

    lines = text.strip().splitlines()
    if not lines:
        return []

    delimiter = _detect_delimiter(lines[0])
    reader = csv.DictReader(lines, delimiter=delimiter)
    return list(reader)


def _build_description(row: dict[str, str]) -> str | None:
    """Build a description from extra CSV fields (city, NUTS, size)."""
    parts: list[str] = []
    city = row.get("city", "").strip()
    postcode = row.get("postcode", "").strip()
    nuts = row.get("nuts_code", "").strip()
    size = row.get("size", "").strip()

    if city:
        loc = city
        if postcode:
            loc = f"{postcode} {city}"
        parts.append(f"Location: {loc}")
    if nuts:
        parts.append(f"NUTS: {nuts}")
    if size:
        parts.append(f"Size: {size}")
    return "; ".join(parts) if parts else None


class OrganizationCSVLoader:
    """Load organizations from a CSV file into the database.

    Supports two CSV formats:
    1. Simple: tax_id;name;website
    2. Challenge: organisationIdentifier,organisationName,organisationInternetAddress,...
    """

    async def load(self, csv_path: Path) -> LoadResult:
        """Parse CSV and upsert organizations.

        Handles messy tax IDs, duplicate rows, and both CSV formats.
        """
        result = LoadResult()
        rows = _read_csv(csv_path)
        result.total_rows = len(rows)

        if not rows:
            return result

        # Normalize column names to internal keys via alias map
        sample_keys = list(rows[0].keys())
        key_map: dict[str, str] = {}
        for k in sample_keys:
            lower = k.strip().lower().replace(" ", "_")
            mapped = _COLUMN_ALIASES.get(lower, lower)
            key_map[k] = mapped

        # Track seen tax_ids to handle duplicates within the CSV
        seen_tax_ids: set[str] = set()

        async with get_session() as session:
            repo = OrganizationRepository(session)

            for i, row in enumerate(rows, start=1):
                norm = {
                    key_map.get(k, k): (v.strip() if v else "")
                    for k, v in row.items()
                }

                raw_id = norm.get("tax_id", "")
                name = norm.get("name", "").strip()
                website = norm.get("website", "")

                # Validate name
                if not name:
                    result.skipped += 1
                    result.errors.append(f"Row {i}: empty name")
                    continue

                # Extract / validate tax ID
                tax_id: str | None = None
                if TAX_ID_PATTERN.match(raw_id):
                    # Already clean
                    tax_id = raw_id
                else:
                    # Try to extract from messy identifier
                    tax_id = _extract_de_tax_id(raw_id)

                if not tax_id:
                    result.skipped += 1
                    result.errors.append(
                        f"Row {i}: cannot extract tax_id from '{raw_id}'"
                    )
                    continue

                # Skip duplicate within this CSV load
                if tax_id in seen_tax_ids:
                    result.skipped += 1
                    logger.debug("Row %d: duplicate tax_id %s — skipped", i, tax_id)
                    continue
                seen_tax_ids.add(tax_id)

                website_norm = _normalize_website(website)
                description = _build_description(norm)

                try:
                    org, is_new = await repo.upsert(
                        tax_id=tax_id, name=name, website=website_norm
                    )
                    # Set description if we have extra info
                    if description and (is_new or not org.description):
                        org.description = description

                    if is_new:
                        result.inserted += 1
                    else:
                        result.updated += 1
                except Exception as exc:
                    result.skipped += 1
                    result.errors.append(f"Row {i}: {exc}")
                    logger.warning("Error upserting row %d: %s", i, exc)

            await session.commit()

        logger.info(
            "CSV load complete: %d total, %d new, %d updated, %d skipped",
            result.total_rows,
            result.inserted,
            result.updated,
            result.skipped,
        )
        return result
