"""German Tenders Intelligence Platform — CLI entry point."""

import asyncio
import logging
from datetime import date, datetime

import typer
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="tenderx",
    help="German Tenders Intelligence Platform",
    no_args_is_help=False,
    rich_markup_mode="rich",
)
console = Console()


# ============================================================
# Welcome screen
# ============================================================

def _build_banner() -> Text:
    """Build the tenderX ASCII art banner with color-split styling.

    The 'tender' portion renders in bold white; the 'X' portion
    renders in bold bright_blue, giving a branded terminal aesthetic.
    """
    parts_tender = [
        "   _                  _           ",
        "  | |_ ___ _ __   __| | ___ _ __ ",
        "  | __/ _ \\ '_ \\ / _` |/ _ \\ '__|",
        "  | ||  __/ | | | (_| |  __/ |   ",
        "   \\__\\___|_| |_|\\__,_|\\___|_|  ",
    ]
    parts_x = [
        " __  __",
        " \\ \\/ /",
        "  \\  / ",
        "  /  \\ ",
        " /_/\\_\\",
    ]
    banner = Text()
    for i, (tp, xp) in enumerate(zip(parts_tender, parts_x)):
        banner.append(tp, style="bold white")
        banner.append(xp, style="bold bright_blue")
        if i < len(parts_tender) - 1:
            banner.append("\n")
    return banner


def _build_version_line() -> Text:
    """Build the version and subtitle line."""
    line = Text()
    line.append("v0.1.0", style="dim bright_blue")
    line.append("  |  ", style="dim")
    line.append("German Procurement Intelligence Platform", style="dim")
    return line


def show_welcome_screen() -> None:
    """Display the branded tenderX welcome screen with quick-start menu."""
    console.print()

    # ASCII art banner
    console.print(Align.center(_build_banner()))
    console.print()

    # Version + tagline
    console.print(Align.center(_build_version_line()))
    console.print()

    # Separator
    console.print(Rule(characters="-", style="bright_blue"))
    console.print()

    # Quick-start commands
    cmds = Text()
    cmds.append("  Quick Start\n\n", style="bold bright_blue")

    menu_items = [
        ("tenderx ingest run", "Ingest tenders from the procurement API"),
        ("tenderx ingest enrich", "Run AI enrichment on stored tenders"),
        ("tenderx search query", "Semantic + structured tender search"),
        ("tenderx orgs load", "Load organizations from CSV"),
        ("tenderx orgs match --all", "Match organizations to relevant tenders"),
        ("tenderx stats", "Show system statistics"),
        ("tenderx docs analyze", "Analyze document supplier portals"),
        ("tenderx docs download", "Download documents from supplier portal"),
    ]

    max_cmd_len = max(len(cmd) for cmd, _ in menu_items)
    for cmd, desc in menu_items:
        padding = " " * (max_cmd_len - len(cmd) + 4)
        cmds.append(f"  {cmd}", style="bold")
        cmds.append(f"{padding}{desc}\n", style="dim")

    cmds.append("\n")
    help_cmd = "tenderx --help"
    padding = " " * (max_cmd_len - len(help_cmd) + 4)
    cmds.append(f"  {help_cmd}", style="bold yellow")
    cmds.append(f"{padding}Show all commands and detailed usage\n", style="dim")

    console.print(
        Panel(cmds, border_style="bright_blue", expand=False, padding=(1, 2))
    )
    console.print()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """German Tenders Intelligence Platform."""
    if ctx.invoked_subcommand is None:
        show_welcome_screen()


# --- Command groups ---
ingest_app = typer.Typer(help="Tender ingestion commands")
search_app = typer.Typer(help="Search and filter tenders")
orgs_app = typer.Typer(help="Organization management")
docs_app = typer.Typer(help="Document storage commands")
tender_app = typer.Typer(help="Tender inspection commands")

app.add_typer(ingest_app, name="ingest")
app.add_typer(search_app, name="search")
app.add_typer(orgs_app, name="orgs")
app.add_typer(docs_app, name="docs")
app.add_typer(tender_app, name="tender")


# ============================================================
# INGEST commands
# ============================================================

@ingest_app.command("run")
def ingest_run(
    days: int = typer.Option(7, help="Number of days to ingest"),
    date_str: str = typer.Option(None, "--date", help="Specific date (YYYY-MM-DD)"),
    enrich: bool = typer.Option(True, help="Run AI enrichment after ingestion"),
) -> None:
    """Ingest tenders from the German procurement API."""
    from src.ingestion.tender_pipeline import TenderPipeline

    async def _run() -> None:
        pipeline = TenderPipeline()
        if date_str:
            target = date.fromisoformat(date_str)
            console.print(f"Ingesting tenders for {target}...")
            result = await pipeline.run_date(target)
        else:
            console.print(f"Ingesting tenders from last {days} days...")
            result = await pipeline.run(days=days)

        console.print(
            f"\n[green]Done![/green] "
            f"{result.total_fetched} fetched, "
            f"{result.inserted} new, "
            f"{result.updated} updated, "
            f"{result.errors} errors "
            f"({result.duration_seconds:.1f}s)"
        )

        if enrich:
            try:
                from src.ingestion.enrichment import EnrichmentPipeline
                from src.ai.llm_client import OllamaClient

                client = OllamaClient()
                if await client.is_available():
                    console.print("\nRunning AI enrichment...")
                    ep = EnrichmentPipeline(client)
                    er = await ep.run()
                    console.print(
                        f"[green]Enrichment:[/green] "
                        f"{er.succeeded} enriched, "
                        f"{er.failed} failed, "
                        f"{er.skipped} skipped"
                    )
                else:
                    console.print(
                        "[yellow]Ollama not available — skipping enrichment[/yellow]"
                    )
            except Exception as exc:
                console.print(f"[yellow]Enrichment skipped: {exc}[/yellow]")

            # Generate embeddings for enriched tenders
            try:
                from src.search.embeddings import generate_tender_embeddings

                console.print("\nGenerating embeddings...")
                count = await generate_tender_embeddings(limit=500)
                console.print(f"[green]Embeddings:[/green] {count} generated")
            except Exception as exc:
                console.print(f"[yellow]Embeddings skipped: {exc}[/yellow]")

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print("[red]Database not available. Run 'docker compose up -d' first.[/red]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


@ingest_app.command("enrich")
def ingest_enrich() -> None:
    """Run AI enrichment on unenriched tenders."""
    async def _run() -> None:
        from src.ingestion.enrichment import EnrichmentPipeline
        from src.ai.llm_client import OllamaClient

        client = OllamaClient()
        if not await client.is_available():
            console.print("[red]Ollama not available. Start it first.[/red]")
            return

        console.print("Running AI enrichment...")
        ep = EnrichmentPipeline(client)
        result = await ep.run()
        console.print(
            f"[green]Done![/green] "
            f"{result.succeeded} enriched, "
            f"{result.failed} failed, "
            f"{result.skipped} skipped "
            f"({result.duration_seconds:.1f}s)"
        )

    try:
        asyncio.run(_run())
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


# ============================================================
# SEARCH commands
# ============================================================

@search_app.command("query")
def search_query(
    query_text: str = typer.Argument(None, help="Free-text search query"),
    cpv: str = typer.Option(None, help="CPV code filter"),
    nuts: str = typer.Option(None, help="NUTS code filter"),
    min_value: float = typer.Option(None, help="Minimum estimated value"),
    max_value: float = typer.Option(None, help="Maximum estimated value"),
    limit: int = typer.Option(20, help="Maximum results"),
) -> None:
    """Search tenders with semantic and structured filters."""
    from src.search.structured import SearchFilters

    async def _run() -> None:
        from src.search.hybrid import search_hybrid
        from src.db.session import get_session

        filters = SearchFilters(
            cpv_codes=[cpv] if cpv else None,
            nuts_codes=[nuts] if nuts else None,
            min_value=min_value,
            max_value=max_value,
        )

        async with get_session() as session:
            results = await search_hybrid(
                session, query=query_text, filters=filters, limit=limit
            )

        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(title=f"Search Results ({len(results)})")
        table.add_column("Score", width=6)
        table.add_column("Title", max_width=60)
        table.add_column("CPV", width=12)
        table.add_column("Value", width=15)
        table.add_column("Deadline", width=12)

        for r in results:
            t = r.tender
            score = f"{r.semantic_score:.3f}" if r.semantic_score else "-"
            cpv_str = ", ".join((t.cpv_codes or [])[:2])
            value = f"{t.estimated_value:,.0f} {t.currency}" if t.estimated_value else "-"
            deadline = t.submission_deadline.strftime("%Y-%m-%d") if t.submission_deadline else "-"
            table.add_row(score, t.title[:60], cpv_str, value, deadline)

        console.print(table)

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print("[red]Database not available. Run 'docker compose up -d' first.[/red]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


# ============================================================
# ORGS commands
# ============================================================

@orgs_app.command("load")
def orgs_load(
    csv_path: str = typer.Option("organizations.csv", "--csv", help="Path to organizations CSV"),
) -> None:
    """Load organizations from a CSV file."""
    from pathlib import Path

    async def _run() -> None:
        from src.organizations.csv_loader import OrganizationCSVLoader

        loader = OrganizationCSVLoader()
        result = await loader.load(Path(csv_path))

        console.print(
            f"\n[green]Done![/green] "
            f"{result.total_rows} total, "
            f"{result.inserted} new, "
            f"{result.updated} updated, "
            f"{result.skipped} skipped"
        )
        if result.errors:
            console.print(f"[yellow]Errors ({len(result.errors)}):[/yellow]")
            for err in result.errors[:10]:
                console.print(f"  {err}")

    try:
        asyncio.run(_run())
    except FileNotFoundError:
        console.print(f"[red]File not found: {csv_path}[/red]")
    except ConnectionRefusedError:
        console.print("[red]Database not available. Run 'docker compose up -d' first.[/red]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


@orgs_app.command("match")
def orgs_match(
    org_id: str = typer.Option(None, "--org-id", help="Match a specific organization UUID"),
    all_orgs: bool = typer.Option(False, "--all", help="Match all organizations"),
) -> None:
    """Run tender matching for organizations."""
    if not org_id and not all_orgs:
        console.print("[red]Specify --org-id or --all[/red]")
        raise typer.Exit(1)

    async def _run() -> None:
        from uuid import UUID
        from src.matching.matcher import TenderMatcher

        matcher = TenderMatcher()

        if all_orgs:
            console.print("Matching all organizations...")
            results = await matcher.match_all()
            table = Table(title=f"Matching Results ({len(results)})")
            table.add_column("Organization")
            table.add_column("Queries")
            table.add_column("Matches")
            table.add_column("Source")
            for r in results:
                table.add_row(
                    r.organization_name,
                    str(len(r.queries)),
                    str(r.total_matches),
                    r.query_source,
                )
            console.print(table)
        else:
            uid = UUID(org_id)
            console.print(f"Matching organization {uid}...")
            result = await matcher.match_organization(uid)
            console.print(f"\nOrganization: [bold]{result.organization_name}[/bold]")
            console.print(f"Query source: {result.query_source}")
            console.print("\nQueries:")
            for q in result.queries:
                console.print(f"  - {q}")
            console.print(f"\nTotal matches: {result.total_matches}")
            if result.top_matches:
                console.print("\nTop matches:")
                for title, score in result.top_matches[:10]:
                    console.print(f"  {score:.3f} — {title[:70]}")

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print("[red]Database not available. Run 'docker compose up -d' first.[/red]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


# ============================================================
# DOCS commands
# ============================================================

@docs_app.command("analyze")
def docs_analyze() -> None:
    """Analyze document supplier portals."""
    async def _run() -> None:
        from pathlib import Path
        from src.documents.analyzer import SupplierAnalyzer

        analyzer = SupplierAnalyzer()
        stats = await analyzer.analyze()

        if not stats:
            console.print("[yellow]No document portal URLs found.[/yellow]")
            return

        table = Table(title="Document Supplier Analysis")
        table.add_column("Domain")
        table.add_column("Tenders", justify="right")
        table.add_column("%", justify="right")
        for s in stats[:20]:
            table.add_row(s.domain, str(s.tender_count), f"{s.percentage:.1f}%")
        console.print(table)

        out = Path("data/output/supplier_analysis.csv")
        analyzer.export_csv(stats, out)
        console.print(f"\n[green]CSV saved to {out}[/green]")

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print("[red]Database not available. Run 'docker compose up -d' first.[/red]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


@docs_app.command("download")
def docs_download(
    supplier: str = typer.Option(..., help="Supplier domain to download from"),
    limit: int = typer.Option(100, help="Maximum tenders to process"),
) -> None:
    """Download documents from a supplier portal."""
    async def _run() -> None:
        from src.documents.downloader import DocumentDownloader

        dl = DocumentDownloader()
        result = await dl.download_for_supplier(supplier, limit=limit)
        console.print(
            f"\n[green]Done![/green] "
            f"{result.tenders_processed} tenders, "
            f"{result.documents_downloaded} downloaded, "
            f"{result.documents_failed} failed, "
            f"{result.total_bytes:,} bytes"
        )

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print("[red]Database not available. Run 'docker compose up -d' first.[/red]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


# ============================================================
# TENDER commands
# ============================================================

@tender_app.command("show")
def tender_show(
    tender_id: str = typer.Argument(help="Tender UUID"),
) -> None:
    """Show detailed information about a tender."""
    from uuid import UUID

    async def _run() -> None:
        from src.db.repositories import TenderRepository
        from src.db.session import get_session

        async with get_session() as session:
            repo = TenderRepository(session)
            tender = await repo.find_by_id(UUID(tender_id))

        if not tender:
            console.print(f"[red]Tender {tender_id} not found.[/red]")
            return

        lines = [
            f"[bold]Contract:[/bold] {tender.contract_number or '-'}",
            f"[bold]Type:[/bold] {tender.contract_type or '-'}",
            f"[bold]Value:[/bold] {tender.estimated_value or '-'} {tender.currency}",
            f"[bold]Published:[/bold] {tender.publication_date or '-'}",
            f"[bold]Deadline:[/bold] {tender.submission_deadline or '-'}",
            f"[bold]Location:[/bold] {tender.execution_location or '-'}",
            f"[bold]CPV:[/bold] {', '.join(tender.cpv_codes or [])}",
            f"[bold]NUTS:[/bold] {', '.join(tender.nuts_codes or [])}",
            f"[bold]Platform:[/bold] {tender.platform_url or '-'}",
            f"[bold]Docs Portal:[/bold] {tender.document_portal_url or '-'}",
        ]

        if tender.ai_summary:
            lines.append(f"\n[bold]AI Summary:[/bold] {tender.ai_summary}")

        if tender.issuer:
            lines.append(f"\n[bold]Issuer:[/bold] {tender.issuer.name}")
            if tender.issuer.contact_email:
                lines.append(f"[bold]Contact:[/bold] {tender.issuer.contact_email}")

        if tender.lots:
            lines.append(f"\n[bold]Lots ({len(tender.lots)}):[/bold]")
            for lot in tender.lots:
                val = f" — {lot.estimated_value} EUR" if lot.estimated_value else ""
                lines.append(f"  {lot.lot_number}. {lot.title or 'Untitled'}{val}")

        if tender.documents:
            lines.append(f"\n[bold]Documents ({len(tender.documents)}):[/bold]")
            for doc in tender.documents:
                lines.append(f"  - {doc.filename} ({doc.content_type or 'unknown'})")

        console.print(
            Panel("\n".join(lines), title=tender.title[:80], expand=False)
        )

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print("[red]Database not available. Run 'docker compose up -d' first.[/red]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


# ============================================================
# STATS command
# ============================================================

@app.command("stats")
def stats() -> None:
    """Show system statistics."""
    async def _run() -> None:
        from sqlalchemy import func, select
        from src.db.session import get_session
        from src.db.models import (
            Tender, Issuer, Organization, TenderDocument, MatchResult,
        )

        async with get_session() as session:
            tender_count = (await session.execute(select(func.count(Tender.id)))).scalar_one()
            issuer_count = (await session.execute(select(func.count(Issuer.id)))).scalar_one()
            org_count = (await session.execute(select(func.count(Organization.id)))).scalar_one()
            doc_count = (await session.execute(select(func.count(TenderDocument.id)))).scalar_one()
            match_count = (await session.execute(select(func.count(MatchResult.id)))).scalar_one()

            enriched = (await session.execute(
                select(func.count(Tender.id)).where(Tender.ai_summary.isnot(None))
            )).scalar_one()
            embedded = (await session.execute(
                select(func.count(Tender.id)).where(Tender.embedding.isnot(None))
            )).scalar_one()

            min_date = (await session.execute(select(func.min(Tender.publication_date)))).scalar_one()
            max_date = (await session.execute(select(func.max(Tender.publication_date)))).scalar_one()

        table = Table(title="System Statistics")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Tenders", f"{tender_count:,}")
        table.add_row("Total Issuers", f"{issuer_count:,}")
        table.add_row("Total Organizations", f"{org_count:,}")
        table.add_row("Total Documents", f"{doc_count:,}")
        table.add_row("Total Matches", f"{match_count:,}")
        table.add_row("Date Range", f"{min_date or '-'} to {max_date or '-'}")

        pct_enrich = f"{enriched/tender_count*100:.0f}%" if tender_count else "0%"
        pct_embed = f"{embedded/tender_count*100:.0f}%" if tender_count else "0%"
        table.add_row("Enriched", f"{enriched:,} / {tender_count:,} ({pct_enrich})")
        table.add_row("Embedded", f"{embedded:,} / {tender_count:,} ({pct_embed})")

        console.print(table)

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print("[red]Database not available. Run 'docker compose up -d' first.[/red]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


# ============================================================
# PURGE command
# ============================================================

@app.command("purge")
def purge(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete ALL data: database rows, MinIO objects, and generated files."""
    from pathlib import Path

    async def _count() -> dict[str, int]:
        """Gather counts of everything that will be deleted."""
        from sqlalchemy import func, select
        from src.db.session import get_session
        from src.db.models import (
            Tender, Issuer, Organization, TenderDocument, TenderLot, MatchResult,
        )

        async with get_session() as session:
            counts = {}
            counts["tenders"] = (await session.execute(select(func.count(Tender.id)))).scalar_one()
            counts["issuers"] = (await session.execute(select(func.count(Issuer.id)))).scalar_one()
            counts["organizations"] = (await session.execute(select(func.count(Organization.id)))).scalar_one()
            counts["tender_lots"] = (await session.execute(select(func.count(TenderLot.id)))).scalar_one()
            counts["tender_documents"] = (await session.execute(select(func.count(TenderDocument.id)))).scalar_one()
            counts["match_results"] = (await session.execute(select(func.count(MatchResult.id)))).scalar_one()

            enriched = (await session.execute(
                select(func.count(Tender.id)).where(Tender.ai_summary.isnot(None))
            )).scalar_one()
            embedded = (await session.execute(
                select(func.count(Tender.id)).where(Tender.embedding.isnot(None))
            )).scalar_one()
            counts["enriched_tenders"] = enriched
            counts["embedded_vectors"] = embedded

        return counts

    async def _purge_database() -> None:
        """Truncate all tables in dependency order."""
        from sqlalchemy import text
        from src.db.session import get_session

        async with get_session() as session:
            # Order matters: children first, then parents
            tables = [
                "match_results",
                "tender_documents",
                "tender_lots",
                "tenders",
                "issuers",
                "organizations",
            ]
            for table in tables:
                await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            await session.commit()

    def _purge_minio() -> int:
        """Delete all objects from the MinIO bucket. Returns count deleted."""
        try:
            from minio import Minio
            from src.config import settings

            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_user,
                secret_key=settings.minio_password,
                secure=False,
            )
            bucket = settings.minio_bucket
            if not client.bucket_exists(bucket):
                return 0

            objects = list(client.list_objects(bucket, recursive=True))
            for obj in objects:
                client.remove_object(bucket, obj.object_name)
            return len(objects)
        except Exception as exc:
            logger.warning("MinIO purge failed: %s", exc)
            return 0

    def _purge_files() -> list[str]:
        """Delete generated output files. Returns list of deleted paths."""
        deleted: list[str] = []
        output_dir = Path("data/output")
        if output_dir.exists():
            for f in output_dir.iterdir():
                if f.name == ".gitkeep":
                    continue
                f.unlink()
                deleted.append(str(f))
        return deleted

    async def _count_and_purge(do_purge: bool) -> dict[str, int]:
        """Gather counts and optionally purge DB — single event loop for both."""
        counts = await _count()
        if do_purge:
            await _purge_database()
        return counts

    def _show_summary(counts: dict[str, int]) -> tuple[int, int, list]:
        """Display what will be deleted. Returns (total_rows, minio_count, gen_files)."""
        total_rows = sum(v for k, v in counts.items() if k not in ("enriched_tenders", "embedded_vectors"))

        console.print("\n[bold red]PURGE -- The following data will be PERMANENTLY deleted:[/bold red]\n")

        table = Table(title="Database Tables", show_lines=False)
        table.add_column("Table", style="bold")
        table.add_column("Rows", justify="right")
        table.add_row("tenders", f"{counts['tenders']:,}")
        table.add_row("  - with AI summaries", f"{counts['enriched_tenders']:,}")
        table.add_row("  - with embeddings (384-dim vectors)", f"{counts['embedded_vectors']:,}")
        table.add_row("issuers", f"{counts['issuers']:,}")
        table.add_row("organizations", f"{counts['organizations']:,}")
        table.add_row("tender_lots", f"{counts['tender_lots']:,}")
        table.add_row("tender_documents", f"{counts['tender_documents']:,}")
        table.add_row("match_results", f"{counts['match_results']:,}")
        table.add_row("[bold]Total rows[/bold]", f"[bold]{total_rows:,}[/bold]")
        console.print(table)

        # MinIO
        try:
            from minio import Minio
            from src.config import settings as _settings

            client = Minio(
                _settings.minio_endpoint,
                access_key=_settings.minio_user,
                secret_key=_settings.minio_password,
                secure=False,
            )
            bucket = _settings.minio_bucket
            if client.bucket_exists(bucket):
                minio_objects = list(client.list_objects(bucket, recursive=True))
                minio_count = len(minio_objects)
            else:
                minio_count = 0
        except Exception:
            minio_count = 0

        from src.config import settings as _settings
        console.print(f"\n[bold]MinIO bucket[/bold] ({_settings.minio_bucket}): [yellow]{minio_count} objects[/yellow]")

        # Generated files
        output_dir = Path("data/output")
        gen_files = [
            f for f in output_dir.iterdir() if f.name != ".gitkeep"
        ] if output_dir.exists() else []
        if gen_files:
            console.print(f"\n[bold]Generated files[/bold] (data/output/):")
            for f in gen_files:
                size_kb = f.stat().st_size / 1024
                console.print(f"  - {f.name} ({size_kb:.1f} KB)")
        else:
            console.print(f"\n[bold]Generated files[/bold]: none")

        return total_rows, minio_count, gen_files

    try:
        # Step 1: Gather what will be deleted (async — first event loop)
        counts = asyncio.run(_count_and_purge(do_purge=False))

        # Step 2: Show summary (sync — no event loop needed)
        total_rows, minio_count, gen_files = _show_summary(counts)

        # Nothing to delete?
        if total_rows == 0 and minio_count == 0 and not gen_files:
            console.print("\n[green]Nothing to purge -- system is already clean.[/green]")
            return

        # Step 3: Ask for confirmation (sync)
        if not yes:
            console.print("")
            confirm = typer.confirm(
                "Are you sure you want to delete ALL of the above? This cannot be undone",
                default=False,
            )
            if not confirm:
                console.print("[yellow]Aborted.[/yellow]")
                raise typer.Exit(0)

        # Step 4: Execute purge
        console.print("\n[bold]Purging...[/bold]")

        # Database (async — second event loop, need fresh engine)
        if total_rows > 0:
            console.print("  Truncating database tables...", end=" ")
            from src.db.session import reset_engine
            reset_engine()  # dispose old engine bound to closed event loop
            asyncio.run(_count_and_purge(do_purge=True))
            console.print(f"[green]OK[/green] {total_rows:,} rows deleted")

        # MinIO (sync)
        if minio_count > 0:
            console.print("  Removing MinIO objects...", end=" ")
            deleted_count = _purge_minio()
            console.print(f"[green]OK[/green] {deleted_count} objects removed")

        # Files (sync)
        if gen_files:
            console.print("  Deleting generated files...", end=" ")
            deleted_files = _purge_files()
            console.print(f"[green]OK[/green] {len(deleted_files)} files deleted")

        console.print("\n[bold green]Purge complete.[/bold green] System is clean.\n")

    except ConnectionRefusedError:
        console.print("[red]Database not available. Run 'docker compose up -d' first.[/red]")
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


if __name__ == "__main__":
    app()
