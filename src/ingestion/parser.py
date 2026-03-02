"""Parser for CSV ZIP exports from oeffentlichevergabe.de."""

import csv
import io
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


@dataclass
class RawLotRecord:
    """A lot within a tender."""

    lot_number: int
    lot_identifier: str
    title: str | None = None
    description: str | None = None
    estimated_value: Decimal | None = None
    cpv_codes: list[str] = field(default_factory=list)


@dataclass
class RawTenderRecord:
    """Normalized intermediate record from CSV parsing."""

    # Identifiers
    notice_id: str
    notice_version: str
    contract_number: str | None = None
    title: str = ""
    description: str | None = None

    # Dates
    publication_date: date | None = None
    submission_deadline: datetime | None = None

    # Financial
    estimated_value: Decimal | None = None
    currency: str = "EUR"

    # Classification
    cpv_codes: list[str] = field(default_factory=list)
    nuts_codes: list[str] = field(default_factory=list)
    contract_type: str | None = None
    procedure_type: str | None = None

    # Links
    platform_url: str | None = None
    document_portal_url: str | None = None

    # Flags
    eu_funded: bool | None = None
    renewable: bool | None = None
    lots_count: int | None = None
    max_lots_per_bidder: int | None = None

    # Location
    execution_location: str | None = None
    execution_timeline: str | None = None

    # Issuer
    issuer_name: str | None = None
    issuer_email: str | None = None
    issuer_phone: str | None = None
    issuer_address: str | None = None
    issuer_nuts_code: str | None = None
    issuer_org_identifier: str | None = None
    issuer_internet_address: str | None = None

    # Lots
    lots: list[RawLotRecord] = field(default_factory=list)

    # Raw data
    raw_data: dict = field(default_factory=dict)


def _read_csv(zf: zipfile.ZipFile, name: str) -> list[dict]:
    """Read a CSV file from a ZIP, handling encoding."""
    try:
        raw = zf.read(name)
    except KeyError:
        logger.debug("CSV file %s not found in ZIP", name)
        return []

    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        logger.warning("Could not decode %s with any encoding", name)
        return []

    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _safe_decimal(value: str | None) -> Decimal | None:
    """Parse a decimal value, returning None on failure."""
    if not value or not value.strip():
        return None
    try:
        return Decimal(value.strip())
    except InvalidOperation:
        return None


def _safe_int(value: str | None) -> int | None:
    """Parse an integer, returning None on failure."""
    if not value or not value.strip():
        return None
    try:
        return int(float(value.strip()))
    except (ValueError, TypeError):
        return None


def _parse_date(value: str | None) -> date | None:
    """Parse an ISO date string."""
    if not value or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip()).date()
    except (ValueError, TypeError):
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO datetime string."""
    if not value or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except (ValueError, TypeError):
        return None


def parse_csv_zip(zip_bytes: bytes) -> list[RawTenderRecord]:
    """Parse a CSV ZIP export into RawTenderRecord objects.

    Reads notice.csv, purpose.csv, classification.csv, organisation.csv,
    procedure.csv, lot.csv, submissionTerms.csv, placeOfPerformance.csv,
    and duration.csv. Joins data by noticeIdentifier + noticeVersion.

    Args:
        zip_bytes: Raw ZIP file content.

    Returns:
        List of parsed tender records.
    """
    if not zip_bytes:
        return []

    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))

    # Read all CSV files
    notices = _read_csv(zf, "notice.csv")
    purposes = _read_csv(zf, "purpose.csv")
    classifications = _read_csv(zf, "classification.csv")
    organisations = _read_csv(zf, "organisation.csv")
    procedures = _read_csv(zf, "procedure.csv")
    lots_csv = _read_csv(zf, "lot.csv")
    submission_terms = _read_csv(zf, "submissionTerms.csv")
    places = _read_csv(zf, "placeOfPerformance.csv")
    durations = _read_csv(zf, "duration.csv")
    notice_results = _read_csv(zf, "noticeResult.csv")

    # Index by notice key (noticeIdentifier + noticeVersion)
    def nkey(row: dict) -> str:
        return f"{row.get('noticeIdentifier', '')}-{row.get('noticeVersion', '')}"

    # Group purpose rows by notice (lot-level has lotIdentifier set)
    purpose_by_notice: dict[str, list[dict]] = {}
    for row in purposes:
        purpose_by_notice.setdefault(nkey(row), []).append(row)

    # Group classification by notice
    class_by_notice: dict[str, list[dict]] = {}
    for row in classifications:
        class_by_notice.setdefault(nkey(row), []).append(row)

    # Index organisations by notice (first buyer-role org)
    org_by_notice: dict[str, dict] = {}
    for row in organisations:
        key = nkey(row)
        role = row.get("organisationRole", "").lower()
        if key not in org_by_notice and "buyer" in role:
            org_by_notice[key] = row

    # Index procedure by notice
    proc_by_notice: dict[str, dict] = {}
    for row in procedures:
        proc_by_notice[nkey(row)] = row

    # Group lots by notice
    lots_by_notice: dict[str, list[dict]] = {}
    for row in lots_csv:
        lots_by_notice.setdefault(nkey(row), []).append(row)

    # Index submission terms by notice (take first with a date)
    terms_by_notice: dict[str, dict] = {}
    for row in submission_terms:
        key = nkey(row)
        if key not in terms_by_notice and row.get("publicOpeningDate"):
            terms_by_notice[key] = row

    # Group places by notice
    place_by_notice: dict[str, list[dict]] = {}
    for row in places:
        place_by_notice.setdefault(nkey(row), []).append(row)

    # Group durations by notice
    dur_by_notice: dict[str, list[dict]] = {}
    for row in durations:
        dur_by_notice.setdefault(nkey(row), []).append(row)

    # Index notice results by notice
    result_by_notice: dict[str, dict] = {}
    for row in notice_results:
        result_by_notice[nkey(row)] = row

    records: list[RawTenderRecord] = []

    for notice in notices:
        try:
            key = nkey(notice)
            notice_id = notice.get("noticeIdentifier", "")
            version = notice.get("noticeVersion", "")

            # Purpose (notice-level = lotIdentifier is empty)
            purpose_rows = purpose_by_notice.get(key, [])
            notice_purpose = None
            for p in purpose_rows:
                if not p.get("lotIdentifier"):
                    notice_purpose = p
                    break
            if not notice_purpose and purpose_rows:
                notice_purpose = purpose_rows[0]

            title = (notice_purpose or {}).get("title", "") or ""
            description = (notice_purpose or {}).get("description")
            main_nature = (notice_purpose or {}).get("mainNature")
            est_value = _safe_decimal(
                (notice_purpose or {}).get("estimatedValue")
            )
            currency = (
                (notice_purpose or {}).get("estimatedValueCurrency") or "EUR"
            )

            # Also check noticeResult for value
            if est_value is None:
                nr = result_by_notice.get(key, {})
                est_value = _safe_decimal(nr.get("noticeValue"))
                if nr.get("noticeValueCurrency"):
                    currency = nr["noticeValueCurrency"]

            # Classification — CPV codes
            cpv_codes: list[str] = []
            for c in class_by_notice.get(key, []):
                if c.get("classificationType") == "cpv":
                    main = c.get("mainClassificationCode", "")
                    if main:
                        cpv_codes.append(main)
                    additional = c.get("additionalClassificationCodes", "")
                    if additional:
                        cpv_codes.extend(
                            code.strip()
                            for code in additional.split(",")
                            if code.strip()
                        )
            cpv_codes = list(dict.fromkeys(cpv_codes))  # deduplicate

            # NUTS codes from places
            nuts_codes: list[str] = []
            for place in place_by_notice.get(key, []):
                nuts = place.get("placePerformanceCountrySubdivision", "")
                if nuts:
                    nuts_codes.append(nuts)
            nuts_codes = list(dict.fromkeys(nuts_codes))

            # Organisation (issuer)
            org = org_by_notice.get(key, {})
            issuer_internet = org.get("organisationInternetAddress", "")

            # Procedure
            proc = proc_by_notice.get(key, {})
            procedure_type = proc.get("procedureType")
            max_lots = _safe_int(proc.get("lotsMaxAllowed"))
            max_awarded = _safe_int(proc.get("lotsMaxAwarded"))

            # Publication date
            pub_date = _parse_date(notice.get("publicationDate"))

            # Submission deadline from submissionTerms
            terms = terms_by_notice.get(key, {})
            deadline = _parse_datetime(terms.get("publicOpeningDate"))

            # Duration / timeline
            dur_rows = dur_by_notice.get(key, [])
            timeline = None
            if dur_rows:
                d = dur_rows[0]
                period = d.get("durationPeriod", "")
                unit = d.get("durationPeriodUnit", "")
                if period and unit:
                    timeline = f"{period} {unit}"
                elif d.get("durationStartDate") and d.get("durationEndDate"):
                    timeline = f"{d['durationStartDate']} to {d['durationEndDate']}"

            # Location text
            exec_location = None
            if place_by_notice.get(key):
                p = place_by_notice[key][0]
                city = p.get("placePerformanceCity", "")
                nuts_loc = p.get("placePerformanceCountrySubdivision", "")
                exec_location = ", ".join(filter(None, [city, nuts_loc]))

            # Form type for contract classification
            form_type = notice.get("formType", "")
            notice_type = notice.get("noticeType", "")

            # Lots
            lot_rows = lots_by_notice.get(key, [])
            parsed_lots: list[RawLotRecord] = []
            for i, lot_row in enumerate(lot_rows):
                lot_id = lot_row.get("lotIdentifier", "")
                # Find purpose for this lot
                lot_purpose = None
                for p in purpose_rows:
                    if p.get("lotIdentifier") == lot_id:
                        lot_purpose = p
                        break
                # Find classification for this lot
                lot_cpvs: list[str] = []
                for c in class_by_notice.get(key, []):
                    if c.get("lotIdentifier") == lot_id:
                        main = c.get("mainClassificationCode", "")
                        if main:
                            lot_cpvs.append(main)

                parsed_lots.append(
                    RawLotRecord(
                        lot_number=i + 1,
                        lot_identifier=lot_id,
                        title=(lot_purpose or {}).get("title"),
                        description=(lot_purpose or {}).get("description"),
                        estimated_value=_safe_decimal(
                            (lot_purpose or {}).get("estimatedValue")
                        ),
                        cpv_codes=lot_cpvs,
                    )
                )

            # Build platform URL
            platform_url = f"https://www.oeffentlichevergabe.de/ui/de/search/details/{notice_id}"

            # Document portal URL from issuer's internet address or buyer profile
            doc_portal = org.get("buyerProfileURL") or issuer_internet or None

            record = RawTenderRecord(
                notice_id=notice_id,
                notice_version=version,
                contract_number=(notice_purpose or {}).get("internalIdentifier"),
                title=title,
                description=description,
                publication_date=pub_date,
                submission_deadline=deadline,
                estimated_value=est_value,
                currency=currency,
                cpv_codes=cpv_codes,
                nuts_codes=nuts_codes,
                contract_type=main_nature,
                procedure_type=procedure_type,
                platform_url=platform_url,
                document_portal_url=doc_portal,
                eu_funded=None,
                renewable=None,
                lots_count=len(parsed_lots) if parsed_lots else None,
                max_lots_per_bidder=max_lots or max_awarded,
                execution_location=exec_location,
                execution_timeline=timeline,
                issuer_name=org.get("organisationName"),
                issuer_email=None,
                issuer_phone=None,
                issuer_address=", ".join(
                    filter(
                        None,
                        [
                            org.get("organisationPostCode"),
                            org.get("organisationCity"),
                        ],
                    )
                )
                or None,
                issuer_nuts_code=org.get("organisationCountrySubdivision"),
                issuer_org_identifier=org.get("organisationIdentifier"),
                issuer_internet_address=issuer_internet or None,
                lots=parsed_lots,
                raw_data={
                    "notice": dict(notice),
                    "purpose": dict(notice_purpose) if notice_purpose else None,
                    "form_type": form_type,
                    "notice_type": notice_type,
                },
            )
            records.append(record)

        except Exception:
            logger.warning(
                "Failed to parse notice %s",
                notice.get("noticeIdentifier", "?"),
                exc_info=True,
            )

    logger.info("Parsed %d records from CSV ZIP", len(records))
    return records
