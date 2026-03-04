"""English (US) translation strings — canonical reference.

Every other locale file must mirror exactly the same keys.
Rich markup ([green], [bold], etc.) is embedded in values.
Format placeholders use Python .format() syntax: {name}.
"""

STRINGS: dict[str, str] = {
    # ── Welcome Screen ─────────────────────────────────────────
    "welcome.tagline": "German Procurement Intelligence Platform",
    "welcome.quick_start": "Quick Start",
    "welcome.menu.ingest_run": "Ingest tenders from the procurement API",
    "welcome.menu.ingest_enrich": "Run AI enrichment on stored tenders",
    "welcome.menu.search_query": "Semantic + structured tender search",
    "welcome.menu.orgs_load": "Load organizations from CSV",
    "welcome.menu.orgs_match": "Match organizations to relevant tenders",
    "welcome.menu.stats": "Show system statistics",
    "welcome.menu.docs_analyze": "Analyze document supplier portals",
    "welcome.menu.docs_download": "Download documents from supplier portal",
    "welcome.menu.dashboard": "Monitor background jobs in real time",
    "welcome.help_desc": "Show all commands and detailed usage",

    # ── Interactive Shell ──────────────────────────────────────
    "shell.hint": "Type 'help' for commands, 'exit' to quit.",
    "shell.interrupted": "Interrupted.",
    "shell.goodbye": "Goodbye!",
    "shell.invalid_input": "[red]Invalid input: {error}[/red]",

    # ── Help texts — app & groups ──────────────────────────────
    "help.app": "German Tenders Intelligence Platform",
    "help.group.ingest": "Tender ingestion commands",
    "help.group.search": "Search and filter tenders",
    "help.group.orgs": "Organization management",
    "help.group.docs": "Document storage commands",
    "help.group.tender": "Tender inspection commands",

    # ── Help texts — commands ──────────────────────────────────
    "help.cmd.ingest_run": "Ingest tenders from the German procurement API.",
    "help.cmd.ingest_enrich": "Run AI enrichment on unenriched tenders.",
    "help.cmd.dashboard": "Monitor background jobs in real time.",
    "help.cmd.search_query": "Search tenders with semantic and structured filters.",
    "help.cmd.orgs_load": "Load organizations from a CSV file.",
    "help.cmd.orgs_match": "Run tender matching for organizations.",
    "help.cmd.docs_analyze": "Analyze document supplier portals.",
    "help.cmd.docs_download": "Download documents from a supplier portal.",
    "help.cmd.tender_show": "Show detailed information about a tender.",
    "help.cmd.stats": "Show system statistics.",
    "help.cmd.purge": "Delete ALL data: database rows, MinIO objects, and generated files.",
    "help.cmd.lang": "Change the CLI language.",

    # ── Help texts — options ───────────────────────────────────
    "help.opt.days": "Number of days to ingest",
    "help.opt.date": "Specific date (YYYY-MM-DD)",
    "help.opt.enrich": "Run AI enrichment after ingestion",
    "help.opt.query_text": "Free-text search query",
    "help.opt.cpv": "CPV code filter",
    "help.opt.nuts": "NUTS code filter",
    "help.opt.min_value": "Minimum estimated value",
    "help.opt.max_value": "Maximum estimated value",
    "help.opt.limit": "Maximum results",
    "help.opt.csv_path": "Path to organizations CSV",
    "help.opt.org_id": "Match a specific organization UUID",
    "help.opt.all_orgs": "Match all organizations",
    "help.opt.supplier": "Supplier domain to download from",
    "help.opt.tender_id": "Tender UUID",
    "help.opt.verbose": "Show detailed descriptions for each metric",
    "help.opt.yes": "Skip confirmation prompt",
    "help.opt.lang_default": "Reset language to English (default)",
    "help.opt.bg": "Run in background (survives CLI exit, monitor with 'tenderx dashboard')",
    "help.opt.enrich_bg": "Run AI enrichment in background after ingestion",

    # ── Ingest ─────────────────────────────────────────────────
    "ingest.progress_date": "Ingesting tenders for {date}...",
    "ingest.progress_days": "Ingesting tenders from last {days} days...",
    "ingest.done": (
        "\n[green]Done![/green] "
        "{fetched} fetched, {inserted} new, {updated} updated, "
        "{errors} errors ({duration}s)"
    ),
    "ingest.enrichment_running": "\nRunning AI enrichment...",
    "ingest.enrichment_result": (
        "[green]Enrichment:[/green] "
        "{succeeded} enriched, {failed} failed, {skipped} skipped"
    ),
    "ingest.ollama_unavailable": "[yellow]Ollama not available \u2014 skipping enrichment[/yellow]",
    "ingest.enrichment_skipped": "[yellow]Enrichment skipped: {error}[/yellow]",
    "ingest.embeddings_running": "\nGenerating embeddings...",
    "ingest.embeddings_result": "[green]Embeddings:[/green] {count} generated",
    "ingest.embeddings_skipped": "[yellow]Embeddings skipped: {error}[/yellow]",

    # ── Ingest — enrich subcommand ─────────────────────────────
    "ingest.enrich_ollama_unavailable": "[red]Ollama not available. Start it first.[/red]",
    "ingest.enrich_running": "Running AI enrichment...",
    "ingest.enrich_done": (
        "[green]Done![/green] "
        "{succeeded} enriched, {failed} failed, {skipped} skipped ({duration}s)"
    ),

    # ── Search ─────────────────────────────────────────────────
    "search.no_results": "[yellow]No results found.[/yellow]",
    "search.table_title": "Search Results ({count})",
    "search.col_score": "Score",
    "search.col_title": "Title",
    "search.col_cpv": "CPV",
    "search.col_value": "Value",
    "search.col_deadline": "Deadline",

    # ── Organizations ──────────────────────────────────────────
    "orgs.load_done": (
        "\n[green]Done![/green] "
        "{total} total, {inserted} new, {updated} updated, {skipped} skipped"
    ),
    "orgs.load_errors": "[yellow]Errors ({count}):[/yellow]",
    "orgs.file_not_found": "[red]File not found: {path}[/red]",
    "orgs.match_specify": "[red]Specify --org-id or --all[/red]",
    "orgs.match_all_progress": "Matching all organizations...",
    "orgs.match_table_title": "Matching Results ({count})",
    "orgs.match_col_organization": "Organization",
    "orgs.match_col_queries": "Queries",
    "orgs.match_col_matches": "Matches",
    "orgs.match_col_source": "Source",
    "orgs.match_one_progress": "Matching organization {uid}...",
    "orgs.match_one_org": "\nOrganization: [bold]{name}[/bold]",
    "orgs.match_one_source": "Query source: {source}",
    "orgs.match_one_queries": "\nQueries:",
    "orgs.match_one_total": "\nTotal matches: {count}",
    "orgs.match_one_top": "\nTop matches:",

    # ── Documents ──────────────────────────────────────────────
    "docs.no_portals": "[yellow]No document portal URLs found.[/yellow]",
    "docs.analyze_title": "Document Supplier Analysis",
    "docs.col_domain": "Domain",
    "docs.col_tenders": "Tenders",
    "docs.col_percent": "%",
    "docs.csv_saved": "\n[green]CSV saved to {path}[/green]",
    "docs.download_done": (
        "\n[green]Done![/green] "
        "{tenders} tenders, {downloaded} downloaded, "
        "{failed} failed, {bytes} bytes"
    ),

    # ── Tender show ────────────────────────────────────────────
    "tender.not_found": "[red]Tender {id} not found.[/red]",
    "tender.label_contract": "Contract:",
    "tender.label_type": "Type:",
    "tender.label_value": "Value:",
    "tender.label_published": "Published:",
    "tender.label_deadline": "Deadline:",
    "tender.label_location": "Location:",
    "tender.label_cpv": "CPV:",
    "tender.label_nuts": "NUTS:",
    "tender.label_platform": "Platform:",
    "tender.label_docs_portal": "Docs Portal:",
    "tender.label_ai_summary": "AI Summary:",
    "tender.label_issuer": "Issuer:",
    "tender.label_contact": "Contact:",
    "tender.label_lots": "Lots ({count}):",
    "tender.label_documents": "Documents ({count}):",
    "tender.untitled": "Untitled",
    "tender.unknown_type": "unknown",

    # ── Stats ──────────────────────────────────────────────────
    "stats.table_title": "System Statistics",
    "stats.table_title_detailed": "System Statistics  [dim](detailed)[/dim]",
    "stats.col_metric": "Metric",
    "stats.col_value": "Value",
    "stats.col_description": "Description",
    "stats.metric_tenders": "Total Tenders",
    "stats.metric_issuers": "Total Issuers",
    "stats.metric_orgs": "Total Organizations",
    "stats.metric_docs": "Total Documents",
    "stats.metric_matches": "Total Matches",
    "stats.metric_date_range": "Date Range",
    "stats.metric_enriched": "Enriched",
    "stats.metric_embedded": "Embedded",
    "stats.desc_tenders": (
        "Public procurement notices ingested from oeffentlichevergabe.de. "
        "Each tender represents a contracting opportunity published by a German public authority."
    ),
    "stats.desc_issuers": (
        "Distinct contracting authorities (Vergabestellen) that published tenders. "
        "Includes federal, state, and municipal bodies across Germany."
    ),
    "stats.desc_orgs": (
        "Business entities loaded from the challenge CSV. "
        "These are potential bidders whose profiles are matched against available tenders."
    ),
    "stats.desc_docs": (
        "Procurement documents (PDFs, DOCX, etc.) downloaded from supplier portals "
        "and stored in MinIO object storage for offline access."
    ),
    "stats.desc_matches": (
        "Organization-to-tender match results produced by the AI matching pipeline. "
        "Each match includes a similarity score from hybrid semantic + structured search."
    ),
    "stats.desc_date_range": (
        "Publication date span of ingested tenders. Reflects the time window covered "
        "by the data currently in the database."
    ),
    "stats.desc_enriched": (
        "Tenders processed by Ollama (gemma3:4b) to generate an AI summary "
        "and searchable text. Enrichment improves search relevance and readability."
    ),
    "stats.desc_embedded": (
        "Tenders with a 384-dim vector embedding (paraphrase-multilingual-MiniLM-L12-v2) "
        "stored in pgvector, enabling semantic similarity search."
    ),
    "stats.tip": (
        "\n[dim]Tip: run [bold]tenderx stats --verbose[/bold] "
        "for detailed descriptions of each metric.[/dim]"
    ),

    # ── Purge ──────────────────────────────────────────────────
    "purge.header": "\n[bold red]PURGE -- The following data will be PERMANENTLY deleted:[/bold red]\n",
    "purge.db_table_title": "Database Tables",
    "purge.col_table": "Table",
    "purge.col_rows": "Rows",
    "purge.row_tenders": "tenders",
    "purge.row_with_summaries": "  - with AI summaries",
    "purge.row_with_embeddings": "  - with embeddings (384-dim vectors)",
    "purge.row_issuers": "issuers",
    "purge.row_organizations": "organizations",
    "purge.row_tender_lots": "tender_lots",
    "purge.row_tender_documents": "tender_documents",
    "purge.row_match_results": "match_results",
    "purge.total_rows": "[bold]Total rows[/bold]",
    "purge.minio_bucket": "\n[bold]MinIO bucket[/bold] ({bucket}): [yellow]{count} objects[/yellow]",
    "purge.gen_files_header": "\n[bold]Generated files[/bold] (data/output/):",
    "purge.gen_files_none": "\n[bold]Generated files[/bold]: none",
    "purge.nothing_to_purge": "\n[green]Nothing to purge -- system is already clean.[/green]",
    "purge.confirm": "Are you sure you want to delete ALL of the above? This cannot be undone",
    "purge.aborted": "[yellow]Aborted.[/yellow]",
    "purge.purging": "\n[bold]Purging...[/bold]",
    "purge.truncating_db": "  Truncating database tables...",
    "purge.truncating_db_ok": "[green]OK[/green] {count} rows deleted",
    "purge.removing_minio": "  Removing MinIO objects...",
    "purge.removing_minio_ok": "[green]OK[/green] {count} objects removed",
    "purge.deleting_files": "  Deleting generated files...",
    "purge.deleting_files_ok": "[green]OK[/green] {count} files deleted",
    "purge.complete": "\n[bold green]Purge complete.[/bold green] System is clean.\n",

    # ── Dashboard ──────────────────────────────────────────────
    "dashboard.title": "Background Jobs Dashboard",
    "dashboard.col_id": "ID",
    "dashboard.col_type": "Type",
    "dashboard.col_status": "Status",
    "dashboard.col_progress": "Progress",
    "dashboard.col_duration": "Duration",
    "dashboard.col_errors": "Errors",
    "dashboard.no_jobs": "[dim]No background jobs found. Start one with --bg flag.[/dim]",
    "dashboard.exit_hint": "[dim]Press Ctrl+C to exit[/dim]",
    "dashboard.stale_detected": "[yellow]Detected {count} stale job(s) — marked as failed.[/yellow]",

    # ── Background Jobs ───────────────────────────────────────
    "bg.job_started": "[green]Job {job_id} started in background.[/green] Use [bold]tenderx dashboard[/bold] to monitor.",
    "bg.job_type_enrichment": "AI Enrichment",
    "bg.job_type_docs_download": "Docs Download",
    "bg.enrich_started_bg": "[green]Enrichment job {job_id} started in background.[/green] Use [bold]tenderx dashboard[/bold] to monitor.",

    # ── Common ─────────────────────────────────────────────────
    "common.db_unavailable": "[red]Database not available. Run 'docker compose up -d' first.[/red]",
    "common.error": "[red]Error: {error}[/red]",

    # ── Language selection ─────────────────────────────────────
    "lang.menu_title": "Language / Idioma / Sprache",
    "lang.menu_prompt": "Select / Selecione / Wählen (1-4): ",
    "lang.menu_invalid": "[yellow]Please enter 1, 2, 3, or 4.[/yellow]",
    "lang.changed": "\n[green]Language set to {lang_name}.[/green]\n",
    "lang.current": "Current language: [bold]{lang}[/bold] ({code})",
    "lang.reset_to_default": "[green]Language reset to English (en-US).[/green]",
}
