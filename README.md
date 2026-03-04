# German Tenders Intelligence Platform

A procurement intelligence MVP that ingests German public tenders from [oeffentlichevergabe.de](https://www.oeffentlichevergabe.de), enriches them with local AI, and matches them to businesses through hybrid vector + structured search.

**Built for the Augusta Labs AI Challenge** — zero external API costs, fully reproducible.

## Architecture

```
                    oeffentlichevergabe.de API
                            │
                            ▼
                  ┌─────────────────────┐
                  │  Ingestion Pipeline  │  CSV ZIP → parse → upsert
                  └────────┬────────────┘
                           │
                  ┌────────▼────────────┐
                  │   AI Enrichment     │  Ollama (gemma3:4b)
                  │  summary + search   │  → ai_summary, ai_searchable_text
                  └────────┬────────────┘
                           │
                  ┌────────▼────────────┐
                  │  Embedding Gen      │  sentence-transformers (384-dim)
                  │  pgvector storage   │  → Vector(384) column
                  └────────┬────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐   ┌────────────┐   ┌────────────┐
    │ Semantic  │   │ Structured │   │  Matching  │
    │  Search   │   │  Filters   │   │  Pipeline  │
    └──────────┘   └────────────┘   └────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                     ┌──────────┐
                     │   CLI    │  Typer + Rich
                     └──────────┘
```

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12+ |
| Database | PostgreSQL 16 + pgvector |
| Object Storage | MinIO (S3-compatible) |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, CPU) |
| LLM | Ollama `gemma3:4b` (local, zero cost) |
| CLI | Typer + Rich |
| ORM | SQLAlchemy 2.0 (async) |
| HTTP | httpx |
| Containers | Docker Compose |

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- ~8 GB RAM (for Ollama model)
- ~2 GB disk (for embedding model + Ollama)

## Quick Start

```bash
# 1. Clone and enter project
cd german-tenders
# (or: git clone https://github.com/joaogutierrre/german-tenders.git && cd german-tenders)

# 2. Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Start services
docker compose up -d

# 5. Run setup (migrations, Ollama model pull, MinIO bucket)
bash scripts/setup.sh
# Or on Windows, run each step manually:
#   alembic upgrade head
#   curl http://localhost:11434/api/pull -d '{"name":"gemma3:4b"}'

# 6. Launch the interactive shell (first run shows a language selection menu)
tenderx
# — or run individual commands directly —

# 7. Ingest tenders (last 3 days, with AI enrichment)
tenderx ingest run --days 3

# 8. Load organizations
tenderx orgs load --csv organizations.csv

# 9. Search tenders
tenderx search query "IT consulting public administration"

# 10. Match organizations to tenders
tenderx orgs match --all

# 11. View statistics
tenderx stats
tenderx stats --verbose   # adds a description column for each metric
```

> **pgAdmin** is available at http://localhost:5050 (`admin@tenderx.dev` / `admin`) for database inspection.

## CLI Reference

| Command | Description |
|---|---|
| `tenderx ingest run --days N` | Ingest tenders from last N days |
| `tenderx ingest run --date YYYY-MM-DD` | Ingest tenders for a specific date |
| `tenderx ingest run --no-enrich` | Ingest without AI enrichment |
| `tenderx ingest run --enrich-bg` | Offload enrichment to a background job |
| `tenderx ingest enrich` | Run AI enrichment on unenriched tenders |
| `tenderx search query "..."` | Semantic + structured search |
| `tenderx search query --cpv 72000000` | Filter by CPV code |
| `tenderx search query --nuts DE212` | Filter by NUTS region |
| `tenderx search query --max-value 500000` | Filter by value |
| `tenderx orgs load --csv PATH` | Load organizations from CSV |
| `tenderx orgs match --org-id UUID` | Match one organization |
| `tenderx orgs match --all` | Match all organizations |
| `tenderx docs analyze` | Analyze document supplier portals |
| `tenderx docs download --supplier DOMAIN` | Download documents from portal |
| `tenderx tender show UUID` | Show full tender details |
| `tenderx stats` | System statistics overview |
| `tenderx stats --verbose` | Stats with metric descriptions |
| `tenderx dashboard` | Live monitor for background jobs |
| `tenderx lang` | Change CLI language interactively |
| `tenderx lang --default` | Reset language to English (en-US) |
| `tenderx purge` | Delete ALL data (DB + MinIO + files) with confirmation |
| `tenderx purge --yes` | Purge without confirmation prompt |

## Data Source

The platform uses the **oeffentlichevergabe.de** bulk export API:

```
GET /api/notice-exports?pubDay=YYYY-MM-DD&format=csv.zip
```

Each daily export contains ~19 normalized CSV files (~70 notices/day). Data available since 2022-12-01.

## Data Model

- **tenders** — Core tender data with CPV codes, NUTS codes, values, deadlines, AI summary, vector embeddings
- **issuers** — Contracting authorities
- **organizations** — Businesses to match against tenders
- **tender_lots** — Individual lots within a tender
- **tender_documents** — Documents stored in MinIO
- **match_results** — Organization-to-tender matches with similarity scores
- **background_jobs** — Long-running tasks (enrichment, downloads) tracked by the `dashboard` command

## Architecture Decisions

1. **CSV over OCDS JSON** — The API's CSV export is pre-normalized into relational tables, making it simpler to parse than the nested OCDS JSON format.

2. **pgvector over external vector DB** — Single PostgreSQL instance handles both structured queries and vector similarity search, reducing operational complexity.

3. **Hybrid search** — Combines SQL WHERE clauses (CPV, NUTS, value range) with cosine similarity ranking for relevance.

4. **Local LLM (Ollama)** — Zero API costs. Summaries and searchable text generated locally with gemma3:4b.

5. **CLI-first** — Typer CLI as primary interface. No web server needed for the MVP.

6. **Graceful degradation** — Pipeline continues if Ollama is down (skips enrichment), if MinIO is down (skips document storage), or if individual tenders fail (logs and continues).

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_enrichment.py -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing
```

177 unit tests covering: configuration, models, prompts, LLM client, enrichment pipeline, CSV loading, search filters, cosine similarity, embeddings, query generation, matching, document analysis, i18n catalog completeness and locale switching. Integration tests auto-skip if Docker PostgreSQL is unavailable.

## Known Limitations

- Ollama enrichment is slow (~5-10 seconds per tender on CPU)
- Embedding model loads on first search (~30s warmup)
- No web UI (CLI only)
- Document downloading depends on supplier portal structure (HTML scraping)
- No incremental embedding updates (re-generates all unembedded on each run)

## Project Structure

```
src/
├── config.py              # pydantic-settings configuration
├── ai/
│   ├── llm_client.py      # Ollama wrapper
│   └── prompts.py         # Centralized prompt templates
├── background/
│   ├── manager.py         # Spawn & track background jobs via multiprocessing
│   └── worker.py          # Worker process (enrichment, docs_download)
├── db/
│   ├── models.py          # 7 SQLAlchemy models (incl. BackgroundJob)
│   ├── session.py         # Async engine + session
│   └── repositories.py    # Data access layer
├── i18n/
│   ├── __init__.py        # tr() lookup, locale save/load
│   ├── en_us.py           # English (canonical)
│   ├── pt_br.py           # Brazilian Portuguese
│   ├── pt_pt.py           # European Portuguese
│   └── de_de.py           # German
├── ingestion/
│   ├── api_client.py      # oeffentlichevergabe.de API client
│   ├── parser.py          # CSV ZIP parser
│   ├── tender_pipeline.py # Ingestion orchestration
│   └── enrichment.py      # AI enrichment pipeline
├── organizations/
│   └── csv_loader.py      # Organization CSV import
├── search/
│   ├── embeddings.py      # sentence-transformers wrapper
│   ├── structured.py      # SQL filter builder
│   ├── semantic.py        # pgvector similarity search
│   └── hybrid.py          # Combined search
├── matching/
│   ├── query_generator.py # LLM-powered query generation
│   └── matcher.py         # Organization matching pipeline
└── documents/
    ├── analyzer.py        # Supplier portal analysis
    ├── storage.py         # MinIO wrapper
    └── downloader.py      # Document scraper + downloader
```

## License

Built for the Augusta Labs AI Challenge.
