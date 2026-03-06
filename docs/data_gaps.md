# Data Gaps & Fallback Strategies

This document describes which fields required by the challenge are available from the oeffentlichevergabe.de API, which are missing, and what strategies we use to work around the gaps.

## Data Source Overview

The platform uses two export formats from the oeffentlichevergabe.de bulk API:

| Format | Endpoint | Content |
|--------|----------|---------|
| **CSV ZIP** | `/api/notice-exports?format=csv.zip` | ~19 normalized CSV files per day (notice.csv, purpose.csv, classification.csv, organisation.csv, procedure.csv, lot.csv, submissionTerms.csv, placeOfPerformance.csv, duration.csv, noticeResult.csv, etc.) |
| **OCDS ZIP** | `/api/notice-exports?format=ocds.zip` | Open Contracting Data Standard JSON with `releases[].tender.documents[]` arrays |

Data is available since **2022-12-01**, with typically **~70 notices/day**.

---

## Field-by-Field Analysis

### Fully Available from CSV API

| Challenge Requirement | Source CSV | Field(s) | Notes |
|----------------------|-----------|----------|-------|
| Contract number | purpose.csv | `internalIdentifier` | Not always present (~60% coverage) |
| Title | purpose.csv | `title` | Always present. In German. |
| CPV codes | classification.csv | `mainClassificationCode`, `additionalClassificationCodes` | Both notice-level and lot-level CPV codes captured |
| Estimated value | purpose.csv, noticeResult.csv | `estimatedValue`, `noticeValue` | Falls back to noticeResult if purpose is empty (~45% have a value) |
| Currency | purpose.csv | `estimatedValueCurrency` | Defaults to EUR when missing |
| Publication date | notice.csv | `publicationDate` | Always present |
| Submission deadline | submissionTerms.csv | `publicOpeningDate` | ~85% coverage |
| Execution timeline | duration.csv | `durationPeriod` + `durationPeriodUnit`, or `durationStartDate`/`durationEndDate` | ~70% coverage |
| Execution location | placeOfPerformance.csv | `placePerformanceCity`, `placePerformanceCountrySubdivision` | City + NUTS code |
| NUTS codes | placeOfPerformance.csv | `placePerformanceCountrySubdivision` | DE-level subdivision codes |
| Contract type | purpose.csv | `mainNature` | works/services/supplies |
| Lots structure | lot.csv + purpose.csv | Lot identifier, title, description, value per lot | Full lot-level data available |
| Max lots per bidder | procedure.csv | `lotsMaxAllowed`, `lotsMaxAwarded` | ~20% of multi-lot tenders specify this |
| Platform URL | *constructed* | — | Built from notice ID: `https://www.oeffentlichevergabe.de/ui/de/search/details/{noticeId}` |
| Issuer name | organisation.csv | `organisationName` (buyer role) | Always present |
| Issuer address | organisation.csv | `organisationPostCode`, `organisationCity` | Combined into address string |
| Issuer NUTS code | organisation.csv | `organisationCountrySubdivision` | ~90% coverage |
| Issuer identifier | organisation.csv | `organisationIdentifier` | National org ID |
| Description | purpose.csv | `description` | ~80% have a description; often in German |
| Procedure type | procedure.csv | `procedureType` | open, restricted, negotiated, etc. |

### Available via OCDS Enrichment (Secondary Source)

| Challenge Requirement | Source | Field(s) | Strategy |
|----------------------|--------|----------|----------|
| **Document portal URL** | OCDS ZIP | `releases[].tender.documents[].url` | ~73% of notices include document URLs. These are **tender-specific** portal pages (e.g., `deutsche-evergabe.de/dashboards/dashboard_off/{uuid}`), unlike the generic issuer websites in CSV. Enriched during ingestion after CSV processing. |

### NOT Available from API (Gaps)

| Challenge Requirement | Available? | Fallback Strategy |
|----------------------|-----------|-------------------|
| **EU-funded** (`eu_funded`) | **No** | The CSV export does not include an EU-funding flag. The OCDS format does not reliably include this either. We store `NULL` in the database. **Potential future strategy:** scrape the tender detail page at `oeffentlichevergabe.de/ui/de/search/details/{id}` where this information is sometimes displayed in a "Finanzierung" section. See `src/ingestion/scraper.py` for the scraping fallback module. |
| **Renewable** (`renewable`) | **No** | No field in either CSV or OCDS indicates whether a contract is renewable. We store `NULL`. **Potential future strategy:** parse the tender description text with an LLM to detect renewal clauses (e.g., "Verlaengerungsoption", "optional renewal"). This would be part of AI enrichment but is not implemented due to accuracy concerns with automated extraction. |
| **Award criteria** (`award_criteria`) | **Partial** | The CSV export includes some award criteria information in purpose.csv but the structure is inconsistent. We store the raw data in `raw_data` JSON for future extraction but do not populate the `award_criteria` field systematically. |
| **Issuer contact email** | **No** | The CSV export does not include email addresses for contracting authorities. We store `NULL`. Could potentially be scraped from the platform UI or from the issuer's website. |
| **Issuer contact phone** | **No** | Same as email — not available in the CSV export. |

---

## Document Portal URL Problem & Solution

### The Problem

The CSV export provides two URL-like fields for organizations:

1. `buyerProfileURL` — the buyer's procurement profile page (e.g., `https://www.deutschebahn.com/bieterportal/`)
2. `organisationInternetAddress` — the organization's general website (e.g., `https://www.stadt-muenchen.de`)

Neither of these points to the **specific tender's documents**. They are generic issuer websites, which is why the initial document downloader produced zero results — it was scraping corporate homepages instead of document portals.

### The Solution: OCDS Enrichment

The OCDS export format contains `tender.documents[]` arrays with URLs that point to the **actual document portals** for each specific tender. These URLs typically follow patterns like:

- `https://www.deutsche-evergabe.de/dashboards/dashboard_off/{uuid}`
- `https://www.subreport.de/E{id}`
- `https://www.dtvp.de/Satellite/notice/{id}/documents`
- `https://vergabe.autobahn.de/NetServer/TenderingProcedureDetails?function=_Details&TenderOID={id}`

Our pipeline now:
1. Fetches the CSV ZIP (structured data ingestion)
2. Fetches the OCDS ZIP (document URL enrichment)
3. Matches OCDS notice IDs to ingested tenders
4. Updates `document_portal_url` with the OCDS URL when it's more specific than the CSV-sourced URL

This enrichment runs automatically during `tenderx ingest run` and updates ~73% of tenders with correct document portal URLs.

---

## Scraping Fallback Strategy

For fields not available via either API format, we maintain a scraping fallback module (`src/ingestion/scraper.py`) that can extract data from the oeffentlichevergabe.de web interface.

### Currently Implemented Scraping Targets

| Field | URL Pattern | Selector Strategy |
|-------|------------|-------------------|
| EU-funded flag | `/ui/de/search/details/{noticeId}` | Look for "EU-funded" / "EU-finanziert" badge in the detail page |
| Award criteria | `/ui/de/search/details/{noticeId}` | Parse the "Zuschlagskriterien" section |

### Why Scraping is Limited

1. **Rate limiting:** The oeffentlichevergabe.de platform applies rate limits. Scraping hundreds of tenders would be slow and risk IP blocking.
2. **HTML structure changes:** The platform uses a JavaScript-rendered SPA-like UI with dynamic content loading. HTML selectors are fragile and break with platform updates.
3. **Diminishing returns:** For an MVP, the API data covers the most critical fields. The two missing boolean fields (`eu_funded`, `renewable`) add minimal value for matching and search compared to the engineering effort of reliable scraping.
4. **Challenge guidelines:** The challenge explicitly acknowledges that "some fields may not be available at all" and values documenting the reasoning over forcing unreliable extraction.

### Recommended Future Improvements

1. **EU-funding detection via LLM:** Add a targeted prompt to the AI enrichment pipeline that analyzes the tender description for EU-funding indicators (e.g., "EFRE", "ESF", "Horizon Europe", "EU-finanziert").
2. **Renewal detection via LLM:** Similarly, detect renewal options by analyzing description text for keywords like "Verlaengerungsoption", "optional renewal period", "Rahmenvereinbarung" (framework agreement).
3. **Headless browser scraping:** Use Playwright for reliable JavaScript-rendered content extraction, with proper rate limiting and caching.

---

## Data Quality Observations

Based on analysis of real API data (~70 notices/day):

| Metric | Observation |
|--------|-------------|
| **Titles** | Always present, in German. Quality varies from descriptive to bureaucratic reference codes. |
| **Descriptions** | Present in ~80% of notices. Length ranges from one sentence to several paragraphs. In German. |
| **CPV codes** | Present in ~95% of notices. Useful for structured filtering but sometimes too generic (e.g., `45000000` = "Construction work"). |
| **Values** | Only ~45% include an estimated value. Some tenders intentionally hide values for competitive reasons. |
| **NUTS codes** | Present in ~85% of notices. Granularity varies (DE2 vs DE212). |
| **Document URLs (OCDS)** | ~73% of notices include document URLs in the OCDS format. The remaining 27% either have no documents or use portals not captured in the OCDS metadata. |
| **Lot structure** | ~35% of tenders are divided into lots. Lot-level detail (title, description, value) is generally complete when lots exist. |

## Summary

The oeffentlichevergabe.de API provides good coverage of the most critical procurement data fields through its CSV and OCDS export formats. The main gaps are:

1. **EU-funding flag** — Not in API; would require scraping or LLM-based detection
2. **Renewable flag** — Not in API; would require NLP analysis of descriptions
3. **Issuer contact details** — Emails and phones not exported
4. **Award criteria weights** — Inconsistent structure in API

Our approach prioritizes reliable data from the API over fragile scraping, uses OCDS as a secondary enrichment source for document URLs, and documents gaps transparently rather than implementing unreliable workarounds.
