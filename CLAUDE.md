# CLAUDE.md — German Tenders AI Challenge

## Project Identity

This is a **Python MVP** for the Augusta Labs AI Challenge: a procurement intelligence platform that ingests German public tenders, enriches them with AI, and matches them to businesses through intelligent search.

**Repository:** `german-tenders/`
**Language:** Python 3.12
**Architecture:** Modular monolith with CLI interface

---

## Critical Constraints

- **ZERO COST:** No paid APIs. All AI runs locally (Ollama + sentence-transformers). No OpenAI, no Anthropic API, no cloud services.
- **REPRODUCIBLE:** Any evaluator must clone the repo, run `docker compose up` + one setup script, and have a working demo in minutes.
- **PRAGMATIC:** Ship working software. Do NOT over-engineer. Get end-to-end pipeline working before polishing anything.
- **MINIMUM 8GB RAM** assumed on evaluator machine.

---

## Tech Stack (Do NOT Deviate)

| Component | Technology | Notes |
|---|---|---|
| Language | Python 3.12 | Use type hints everywhere |
| Database | PostgreSQL 16 + pgvector | Single DB for structured + vector search |
| Object Storage | MinIO | S3-compatible, local Docker |
| Embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 384-dim, multilingual, runs on CPU |
| Summarization | Ollama `gemma3:4b` | Local LLM, no API keys |
| CLI | Typer | Main interface |
| HTTP Client | httpx | Async-capable |
| Scraping | BeautifulSoup4 | HTML parsing |
| ORM | SQLAlchemy 2.0 | Async support, use mapped_column |
| Migrations | Alembic | Version-controlled schema |
| Settings | pydantic-settings | .env file loading |
| Containers | Docker Compose | PostgreSQL + MinIO + Ollama |

---

## Project Structure

```
german-tenders/
├── docker-compose.yml
├── .env.example
├── .env                        # gitignored
├── CLAUDE.md                   # Project instructions (stays at root)
├── organizations.csv           # Challenge CSV (at project root, NOT in data/)
├── pyproject.toml              # use poetry or pip with pyproject.toml
├── alembic.ini
├── README.md
├── knowledge/                  # Documentation and guides
│   ├── arquitetura_mvp_german_tenders.md  # Architecture doc (PT-BR)
│   ├── PLANO_IMPLEMENTACAO.md  # Implementation plan (PT-BR)
│   └── guia_testes_manuais.md  # Manual testing guide (PT-BR)
├── alembic/
│   ├── env.py
│   └── versions/
├── src/
│   ├── __init__.py
│   ├── config.py               # pydantic-settings, auto-detect RAM for model selection
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   ├── session.py          # Engine + session factory
│   │   └── repositories.py    # Data access layer (no raw SQL in other modules)
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── api_client.py       # oeffentlichevergabe.de API client
│   │   ├── parser.py           # Parse CSV ZIP from API into RawTenderRecord
│   │   ├── scraper.py          # UI scraping fallback
│   │   ├── tender_pipeline.py  # Orchestration: fetch → parse → enrich → store
│   │   └── enrichment.py       # Ollama calls for summary + searchable text
│   ├── organizations/
│   │   ├── __init__.py
│   │   ├── csv_loader.py       # Parse organizations CSV (simple + challenge format)
│   │   └── website_resolver.py # BONUS: resolve missing websites
│   ├── search/
│   │   ├── __init__.py
│   │   ├── embeddings.py       # sentence-transformers wrapper
│   │   ├── structured.py       # SQL-based filters
│   │   ├── semantic.py         # pgvector cosine similarity (delegates to repository)
│   │   └── hybrid.py           # Combine structured + semantic (main search entry)
│   ├── matching/
│   │   ├── __init__.py
│   │   ├── query_generator.py  # Generate 5 search queries per org
│   │   ├── org_aware_query.py  # BONUS: website-aware query generation
│   │   └── matcher.py          # Execute matching pipeline
│   ├── documents/
│   │   ├── __init__.py
│   │   ├── analyzer.py         # Analyze document hosting suppliers
│   │   ├── downloader.py       # Download from chosen supplier portal
│   │   └── storage.py          # MinIO upload/retrieval
│   └── ai/
│       ├── __init__.py
│       ├── llm_client.py       # Unified Ollama wrapper
│       └── prompts.py          # All prompt templates centralized
├── cli.py                      # Typer CLI entry point
├── scripts/
│   ├── setup.sh                # Full setup: docker + ollama model pull + migrations
│   ├── setup_ollama.sh         # Pull Ollama model
│   └── seed_db.py              # Seed database with sample data
├── data/
│   └── output/                 # Generated CSVs (supplier analysis, etc.)
├── docs/
│   └── data_gaps.md            # BONUS: fallback strategies documentation
└── tests/
    ├── __init__.py
    ├── conftest.py             # Fixtures: test DB, mock Ollama
    ├── fixtures/
    │   └── sample_csv.zip      # Real API response fixture (1247 records)
    ├── test_ingestion.py
    ├── test_search.py
    ├── test_organizations.py
    ├── test_matching.py
    ├── test_models.py
    └── test_integration.py     # Integration tests (requires Docker PostgreSQL)
```

---

## Database Schema

Use SQLAlchemy 2.0 with `mapped_column`. All IDs are UUID. Use `pgvector` for embedding columns.

### Tables

**tenders**
- `id`: UUID, PK, default uuid4
- `source_id`: String(200), unique, not null (composite key: `{notice_id}-{notice_version}`)
- `contract_number`: String(100), nullable, index
- `title`: Text, not null
- `description`: Text, nullable
- `cpv_codes`: ARRAY(String), default []
- `estimated_value`: Numeric(15,2), nullable
- `currency`: String(3), default "EUR"
- `award_criteria`: JSON, nullable
- `publication_date`: Date, nullable
- `submission_deadline`: DateTime(timezone=True), nullable
- `execution_timeline`: String(200), nullable
- `execution_location`: Text, nullable
- `nuts_codes`: ARRAY(String), default []
- `contract_type`: String(50), nullable (works/services/supplies/concessions)
- `eu_funded`: Boolean, nullable
- `renewable`: Boolean, nullable
- `lots_count`: Integer, nullable
- `max_lots_per_bidder`: Integer, nullable
- `platform_url`: Text, nullable
- `document_portal_url`: Text, nullable
- `ai_summary`: String(300), nullable
- `ai_searchable_text`: Text, nullable
- `embedding`: Vector(384), nullable
- `issuer_id`: UUID, FK → issuers.id, nullable
- `raw_data`: JSON, nullable (store full API response)
- `created_at`: DateTime, default now
- `updated_at`: DateTime, default now, onupdate now

**issuers**
- `id`: UUID, PK
- `name`: Text, not null
- `contact_email`: String(200), nullable
- `contact_phone`: String(50), nullable
- `address`: Text, nullable
- `nuts_code`: String(20), nullable
- `org_identifier`: String(100), nullable, unique

**organizations**
- `id`: UUID, PK
- `tax_id`: String(20), unique, not null (DE-prefixed VAT)
- `name`: Text, not null
- `website`: Text, nullable
- `website_resolved`: Boolean, default False
- `industry_keywords`: ARRAY(String), nullable
- `description`: Text, nullable
- `embedding`: Vector(384), nullable

**tender_lots**
- `id`: UUID, PK
- `tender_id`: UUID, FK → tenders.id, not null, cascade delete
- `lot_number`: Integer, not null
- `title`: Text, nullable
- `description`: Text, nullable
- `estimated_value`: Numeric(15,2), nullable
- `cpv_codes`: ARRAY(String), default []

**tender_documents**
- `id`: UUID, PK
- `tender_id`: UUID, FK → tenders.id, not null
- `filename`: Text, not null
- `content_type`: String(100), nullable
- `storage_key`: Text, not null (MinIO object key)
- `storage_bucket`: String(100), not null
- `source_url`: Text, nullable
- `downloaded_at`: DateTime, not null

**match_results**
- `id`: UUID, PK
- `organization_id`: UUID, FK → organizations.id, not null
- `tender_id`: UUID, FK → tenders.id, not null
- `query_text`: Text, not null
- `similarity_score`: Float, not null
- `matched_at`: DateTime, default now

### Indexes
- `ix_tenders_cpv_codes`: GIN index on tenders.cpv_codes
- `ix_tenders_nuts_codes`: GIN index on tenders.nuts_codes
- `ix_tenders_embedding`: IVFFlat or HNSW on tenders.embedding (create after data is loaded)
- `ix_tenders_submission_deadline`: B-tree on tenders.submission_deadline
- `ix_tenders_publication_date`: B-tree on tenders.publication_date
- `ix_organizations_tax_id`: unique B-tree on organizations.tax_id

---

## Coding Standards

### Python Style
- **Type hints** on all function signatures
- **Docstrings** on all public functions (Google style)
- **No raw SQL** outside of `repositories.py` — use SQLAlchemy ORM or repository methods
- **Logging** via `structlog` or standard `logging` with structured format
- **Error handling:** never swallow exceptions silently. Log and re-raise or handle gracefully.
- **No print statements** — use logger or Typer's `rich` console

### Imports
```python
# Standard library
from datetime import datetime
from uuid import uuid4

# Third party
import httpx
from sqlalchemy import select
from sentence_transformers import SentenceTransformer

# Local
from src.config import settings
from src.db.models import Tender
```

### Configuration Pattern
```python
# src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "german_tenders"
    db_user: str = "app"
    db_password: str = "changeme"
    
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimension: int = 384
    
    minio_endpoint: str = "localhost:9000"
    minio_user: str = "minioadmin"
    minio_password: str = "changeme"
    minio_bucket: str = "tender-documents"
    
    ingestion_batch_size: int = 100
    ingestion_default_days: int = 7

    class Config:
        env_file = ".env"

settings = Settings()
```

### Repository Pattern
```python
# All DB access goes through repositories
class TenderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_from_raw(self, record: RawTenderRecord, issuer: Issuer | None) -> Tender: ...
    async def find_by_id(self, tender_id: UUID) -> Tender | None: ...
    async def find_unenriched(self, limit: int = 100) -> list[Tender]: ...
    async def find_unembedded(self, limit: int = 100) -> list[Tender]: ...
    async def update_enrichment(self, tender_id: UUID, summary: str, searchable_text: str) -> None: ...
    async def update_embedding(self, tender_id: UUID, embedding: list[float]) -> None: ...
    async def search_by_vector(self, query_embedding: list[float], limit: int = 20) -> list[tuple[UUID, float]]: ...
    async def count(self) -> int: ...
```

### pgvector SQL Syntax
When writing raw SQL with `text()` for pgvector operations, **always** use `cast(:param as type)` syntax,
**never** `::type` suffix — SQLAlchemy's `bindparams()` confuses `::type` with bind parameter names.
```python
# CORRECT
text("... cast(:qvec as vector) ...").bindparams(qvec=str(embedding))
text("... cast(:tid as uuid) ...").bindparams(tid=str(tender_id))

# WRONG — will raise KeyError
text("... :qvec::vector ...").bindparams(qvec=str(embedding))
```

### asyncio.run() and Engine Reset
When calling `asyncio.run()` multiple times in the same process (e.g. the `purge` CLI command),
the SQLAlchemy async engine's connection pool gets bound to the first event loop. After that loop
closes, subsequent `asyncio.run()` calls fail with `'NoneType' object has no attribute 'send'`.

**Solution:** call `reset_engine()` from `src.db.session` between `asyncio.run()` calls:
```python
from src.db.session import reset_engine

asyncio.run(first_async_task())     # first event loop — works
reset_engine()                       # discard engine bound to closed loop
asyncio.run(second_async_task())    # new event loop — works with fresh engine
```

**Important:** `reset_engine()` creates a brand-new engine without calling `dispose()` on the old
one (because `dispose()` tries to close asyncpg connections synchronously, raising MissingGreenlet).
This is safe for CLI use where the process exits shortly after.

### Ollama Client Pattern
```python
# src/ai/llm_client.py
import httpx
from src.config import settings

class OllamaClient:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
    
    async def generate(self, prompt: str, system: str = "") -> str:
        """Call Ollama /api/generate endpoint."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                }
            )
            response.raise_for_status()
            return response.json()["response"]
```

### Embeddings Pattern
```python
# src/search/embeddings.py
from sentence_transformers import SentenceTransformer
from src.config import settings

# Singleton — load model once
_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model

def encode_text(text: str) -> list[float]:
    model = get_model()
    return model.encode(text, normalize_embeddings=True).tolist()

def encode_batch(texts: list[str]) -> list[list[float]]:
    model = get_model()
    return model.encode(texts, normalize_embeddings=True, batch_size=64).tolist()
```

---

## API Data Source

**Primary:** `https://www.oeffentlichevergabe.de/api/`
- Swagger: `https://oeffentlichevergabe.de/documentation/swagger-ui/opendata/index.html#/`
- The API uses OCDS (Open Contracting Data Standard) format.
- Not all fields exist in the API — some require scraping the UI at `https://www.oeffentlichevergabe.de`

**Key API endpoint:**
- `/api/notices-csv?date=YYYY-MM-DD` — returns a ZIP file containing CSV data for that day
- The API returns **CSV inside ZIP**, not JSON. The parser (`src/ingestion/parser.py`) handles ZIP extraction and CSV parsing into `RawTenderRecord` dataclasses.
- A real fixture is saved at `tests/fixtures/sample_csv.zip` (1247 records) for deterministic testing.

**Organizations CSV (Challenge format):**
- Located at project root: `organizations.csv` (NOT in `data/`)
- Columns: `organisationIdentifier`, `organisationName`, `organisationInternetAddress`, `organisationCity`, `organisationPostCode`, `organisationCountrySubdivision`, `organisationCountryCode`, `winnerSize`, `organisationRole`
- Tax IDs are messy (e.g. `DE 124 469 636-00001`, `UStID. DE130487158`) — the CSV loader extracts `DE` + 9 digits via regex.

---

## Prompts (Centralized in src/ai/prompts.py)

All LLM prompts must be in `src/ai/prompts.py`. Never hardcode prompts elsewhere.

### Summary Prompt
```python
TENDER_SUMMARY = """Summarize this German public tender in exactly 1-2 sentences (max 240 characters).
Focus on: what is being procured, by whom, and the key deadline.
Write in English.

Title: {title}
Description: {description}
CPV Codes: {cpv_codes}
Issuer: {issuer_name}
Deadline: {deadline}

Summary:"""
```

### Searchable Text Prompt
```python
TENDER_SEARCHABLE = """Create a rich searchable text for this German public tender.
Include: the type of work/service/supply, industry sector, technical requirements, 
geographic scope, and relevant keywords a business would search for.
Write in English. Max 500 words.

Title: {title}
Description: {description}
CPV Codes: {cpv_codes}
Contract Type: {contract_type}
Location: {location}
NUTS Codes: {nuts_codes}

Searchable text:"""
```

### Query Generator Prompt
```python
GENERATE_QUERIES = """You are an expert in German public procurement.

Given this organization:
- Name: {name}
- Website: {website}
- Description: {description}

Generate exactly 5 realistic search queries this organization would use to find
relevant German public tenders. Return ONLY a JSON array of 5 strings, no other text.

Example: ["IT infrastructure maintenance public sector", "cloud migration government Bavaria", ...]"""
```

---

## CLI Commands (cli.py)

Use Typer with app groups:

```python
import typer
app = typer.Typer(name="tender-cli", help="German Tenders Intelligence Platform")

# Groups
ingest_app = typer.Typer(help="Tender ingestion commands")
search_app = typer.Typer(help="Search and filter tenders")
orgs_app = typer.Typer(help="Organization management")
docs_app = typer.Typer(help="Document storage commands")

app.add_typer(ingest_app, name="ingest")
app.add_typer(search_app, name="search")
app.add_typer(orgs_app, name="orgs")
app.add_typer(docs_app, name="docs")
```

### Required Commands
```
tender-cli ingest run --days 7
tender-cli ingest run --date 2026-02-28
tender-cli search query "IT consulting public administration"
tender-cli search query --cpv 72000000 --nuts DE212 --max-value 500000
tender-cli orgs load --csv organizations.csv
tender-cli orgs match --org-id <uuid>
tender-cli orgs match --all
tender-cli docs analyze
tender-cli docs download --supplier <name> --limit 100
tender-cli tender show <uuid>
tender-cli stats
tender-cli purge                        # Delete ALL data (DB + MinIO + files) with confirmation
tender-cli purge --yes                  # Skip confirmation prompt
```

---

## Implementation Order (STRICT)

Follow this order. Do NOT skip ahead. Each step must work before moving to the next.

### Step 1: Foundation
1. Create `pyproject.toml` with all dependencies
2. Create `docker-compose.yml` (PostgreSQL + pgvector, MinIO, Ollama)
3. Create `.env.example` and `.env`
4. Create `src/config.py` with pydantic-settings
5. Create `src/db/models.py` with all SQLAlchemy models
6. Create `src/db/session.py` with engine + session factory
7. Setup Alembic, generate initial migration
8. Create `scripts/setup.sh` that does everything: docker up, wait for services, pull ollama model, run migrations
9. **VERIFY:** `docker compose up -d && python scripts/setup.sh` works cleanly

### Step 2: API Exploration & Ingestion
1. Manually explore the oeffentlichevergabe.de API with httpx
2. Save sample responses to `data/sample_api_response.json`
3. Create `src/ingestion/api_client.py` — fetch notices with date filtering + pagination
4. Create parser logic to extract structured fields from API response
5. Create `src/db/repositories.py` with TenderRepository.upsert
6. Create `src/ingestion/tender_pipeline.py` — orchestrate: fetch → parse → store
7. Wire up basic CLI: `tender-cli ingest run --days 7`
8. **VERIFY:** Run ingestion and confirm tenders appear in PostgreSQL

### Step 3: AI Enrichment
1. Create `src/ai/prompts.py` with all prompt templates
2. Create `src/ai/llm_client.py` — Ollama wrapper
3. Create `src/ingestion/enrichment.py` — generate summary + searchable text
4. Integrate enrichment into tender_pipeline (process tenders that have `ai_summary IS NULL`)
5. **VERIFY:** Run enrichment on stored tenders, confirm ai_summary and ai_searchable_text are populated

### Step 4: Organizations
1. Create `src/organizations/csv_loader.py` — parse CSV, handle encoding, missing fields
2. Create repository methods for organizations
3. Wire up CLI: `tender-cli orgs load --csv organizations.csv`
4. **VERIFY:** Organizations loaded in DB with tax_id, name, website

### Step 5: Search & Embeddings
1. Create `src/search/embeddings.py` — sentence-transformers wrapper
2. Generate embeddings for all tenders with ai_searchable_text
3. Store embeddings in pgvector column
4. Create `src/search/semantic.py` — vector similarity search
5. Create `src/search/structured.py` — SQL filters (cpv, nuts, price, date, issuer)
6. Create `src/search/hybrid.py` — combine semantic + structured
7. Wire up CLI: `tender-cli search query "..."`
8. **VERIFY:** Search returns relevant results for various queries

### Step 6: Matching
1. Create `src/matching/query_generator.py` — use Ollama to generate 5 queries per org
2. Create `src/matching/matcher.py` — run queries through hybrid search, store results
3. Wire up CLI: `tender-cli orgs match --org-id <id>` and `--all`
4. **VERIFY:** match_results table populated with scored results

### Step 7: Document Analysis & Storage
1. Create `src/documents/analyzer.py` — parse document_portal_url domains, count tenders per supplier
2. Output CSV to `data/output/supplier_analysis.csv`
3. Create `src/documents/storage.py` — MinIO client wrapper
4. Create `src/documents/downloader.py` — download from top supplier portal
5. Wire up CLI: `tender-cli docs analyze` and `tender-cli docs download`
6. **VERIFY:** CSV generated, documents downloaded and stored in MinIO, linked in DB

### Step 8: CLI Polish & Stats
1. Add `tender-cli tender show <id>` — display full tender details
2. Add `tender-cli stats` — total tenders, orgs, docs, match results, date range
3. Add rich formatting (tables, colors) to all CLI output
4. **VERIFY:** All CLI commands work and look professional

### Step 9: README & Packaging
1. Write comprehensive README.md with: project overview, prerequisites, quick start, CLI reference, architecture decisions, known limitations
2. Ensure `.env.example` is complete
3. Test full flow from scratch: clone → setup → ingest → search → match → docs
4. **VERIFY:** A fresh `git clone` + following README gets a working demo in < 5 minutes

---

## Testing Strategy

### Test Organization (152+ tests)

| File | Scope | Docker needed? |
|---|---|---|
| `tests/test_models.py` | ORM model creation, repr, defaults | No |
| `tests/test_ingestion.py` | Parser (real ZIP fixture), API client (mock httpx) | No |
| `tests/test_search.py` | Filters, cosine similarity, embeddings | No |
| `tests/test_organizations.py` | CSV loader (both formats), tax ID extraction | No |
| `tests/test_matching.py` | Query generator, matcher (mock Ollama) | No |
| `tests/test_integration.py` | Repository CRUD, full pipeline with real DB | **Yes** |

### Running Tests
```bash
# Unit tests only (no Docker, ~15s) — ~138 tests
pytest tests/ -v -m "not integration"

# Integration tests (requires: docker compose up -d && alembic upgrade head)
pytest tests/ -v -m integration

# Everything (integration auto-skipped if Docker is down)
pytest tests/ -v
```

### Key Principles
- **Mock Ollama** in unit tests — don't require Ollama running
- **Real ZIP fixture** at `tests/fixtures/sample_csv.zip` (1247 records from real API)
- **Integration tests** marked with `@pytest.mark.integration` — auto-skip if PostgreSQL unreachable
- **Fixtures:** `conftest.py` provides `mock_session`, `mock_ollama`, and DB connection helpers

---

## Error Handling Rules

1. **API failures:** Retry 3 times with exponential backoff (1s, 2s, 4s). Log warning on retry, error on final failure. Never crash the pipeline for a single tender.
2. **Missing fields:** Log as structured warning with tender_id and field name. Store what you have, set missing as NULL.
3. **Ollama timeout:** Default timeout 120s. If Ollama is down, skip enrichment step, log error, continue pipeline.
4. **Malformed CSV rows:** Skip row, log warning with line number and content. Report total skipped at end.
5. **MinIO connection failure:** Log error, skip document storage, continue. Documents can be retried later.

---

## Things to AVOID

- **DO NOT** use OpenAI, Anthropic, or any paid API
- **DO NOT** use Elasticsearch, Pinecone, Weaviate, or any external vector DB
- **DO NOT** create a FastAPI server for the core (CLI is the primary interface)
- **DO NOT** use `print()` — use logging or Typer/Rich console
- **DO NOT** put SQL strings in business logic — all DB access through repositories
- **DO NOT** hardcode prompts in enrichment code — centralize in prompts.py
- **DO NOT** implement bonus features (B1-B5) before ALL core steps (1-9) are complete and verified
- **DO NOT** over-engineer: no abstract factory, no event sourcing, no CQRS, no microservices
- **DO NOT** add dependencies not listed in the tech stack without explicit approval

---

## Definition of Done (per step)

A step is DONE when:
1. Code is written with type hints and docstrings
2. The VERIFY check passes
3. Errors are handled gracefully (no crashes)
4. Relevant CLI commands work as documented
5. A brief commit message describes what was implemented
