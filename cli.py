"""German Tenders Intelligence Platform — CLI entry point."""

import asyncio
import logging
import shlex
import sys
import time
from datetime import date, datetime, timezone

import typer
from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from src.i18n import t as tr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="tenderx",
    help=tr("help.app"),
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
    Uses a large block-letter style for maximum visual impact.
    """
    lines = [
        (" _____                _          ", "  __   __"),
        ("|_   _|__ _ __   __| | ___ _ __", "  \\ \\ / /"),
        ("  | |/ _ \\ '_ \\ / _` |/ _ \\ '__|", "   \\ V / "),
        ("  | |  __/ | | | (_| |  __/ |  ", "   / . \\ "),
        ("  |_|\\___|_| |_|\\__,_|\\___|_|  ", "  /_/ \\_\\"),
    ]
    # Pad tender portion so the X aligns at a fixed column.
    max_tender = max(len(tp) for tp, _ in lines)
    banner = Text()
    for i, (tp, xp) in enumerate(lines):
        banner.append(tp.ljust(max_tender), style="bold white")
        banner.append(xp, style="bold bright_blue")
        if i < len(lines) - 1:
            banner.append("\n")
    return banner


def _build_version_line() -> Text:
    """Build the version and subtitle line."""
    line = Text()
    line.append("v0.1.0", style="dim bright_blue")
    line.append("  |  ", style="dim")
    line.append(tr("welcome.tagline"), style="dim")
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
    cmds.append(f"  {tr('welcome.quick_start')}\n\n", style="bold bright_blue")

    menu_items = [
        ("tenderx ingest run", tr("welcome.menu.ingest_run")),
        ("tenderx ingest enrich", tr("welcome.menu.ingest_enrich")),
        ("tenderx search query", tr("welcome.menu.search_query")),
        ("tenderx orgs load", tr("welcome.menu.orgs_load")),
        ("tenderx orgs match --all", tr("welcome.menu.orgs_match")),
        ("tenderx stats", tr("welcome.menu.stats")),
        ("tenderx docs analyze", tr("welcome.menu.docs_analyze")),
        ("tenderx docs download", tr("welcome.menu.docs_download")),
        ("tenderx dashboard", tr("welcome.menu.dashboard")),
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
    cmds.append(f"{padding}{tr('welcome.help_desc')}\n", style="dim")

    console.print(
        Panel(cmds, border_style="bright_blue", expand=False, padding=(1, 2))
    )
    console.print()


# ============================================================
# Language selection menu
# ============================================================

def _show_language_menu(force: bool = False) -> str | None:
    """Show language selection and return chosen locale, or None if skipped.

    Args:
        force: Show the menu even if a locale is already saved.

    Returns:
        The chosen locale code, or None if the menu was skipped.
    """
    from src.i18n import CONFIG_FILE, SUPPORTED_LOCALES, save_locale, set_locale

    # Already configured? Skip (unless forced).
    if not force and CONFIG_FILE.exists():
        return None

    console.print()
    console.print(Rule(tr("lang.menu_title"), style="bright_blue"))
    console.print()

    locales = list(SUPPORTED_LOCALES.items())
    for i, (code, name) in enumerate(locales, 1):
        console.print(f"  [bold bright_blue]{i}[/bold bright_blue]. {name} ({code})")

    console.print()

    while True:
        try:
            choice = console.input(f"[bold]{tr('lang.menu_prompt')}[/bold]").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "1"
            break

        if choice in ("1", "2", "3", "4"):
            break
        console.print(tr("lang.menu_invalid"))

    idx = int(choice) - 1
    locale_code = locales[idx][0]
    locale_name = locales[idx][1]

    save_locale(locale_code)
    set_locale(locale_code)

    console.print(tr("lang.changed", lang_name=locale_name))
    return locale_code


# ============================================================
# Interactive shell (REPL)
# ============================================================

_in_shell = False


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """German Tenders Intelligence Platform."""
    if ctx.invoked_subcommand is None and not _in_shell:
        show_welcome_screen()


def _run_command(args: list[str]) -> None:
    """Dispatch a command to the Typer app from the interactive shell.

    Resets the SQLAlchemy async engine before each dispatch so that
    successive ``asyncio.run()`` calls inside commands don't fail
    with 'NoneType' object has no attribute 'send' (the pool is
    bound to the previous — now closed — event loop).
    """
    try:
        from src.db.session import reset_engine
        reset_engine()
    except Exception:
        pass  # DB module may not be available yet
    try:
        app(args, standalone_mode=True)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        console.print(f"\n[yellow]{tr('shell.interrupted')}[/yellow]")


def interactive_shell() -> None:
    """Run the interactive tenderX shell (REPL).

    Shows a welcome screen, then loops reading commands from the user
    until 'exit' or 'quit' is entered.  Each command is dispatched to
    the Typer app as if it were typed on the command line.
    """
    global _in_shell
    _in_shell = True

    show_welcome_screen()
    _show_language_menu()

    from src.i18n import load_locale
    load_locale()

    console.print(f"[dim]  {tr('shell.hint')}[/dim]\n")

    while True:
        try:
            user_input = console.input(
                "[bold bright_blue]tenderx[/bold bright_blue] > "
            ).strip()
        except EOFError:
            console.print()
            break
        except KeyboardInterrupt:
            console.print()
            continue

        if not user_input:
            continue

        lower = user_input.lower()
        if lower in ("exit", "quit"):
            break
        if lower == "clear":
            console.clear()
            continue
        if lower == "help":
            _run_command(["--help"])
            continue

        try:
            args = shlex.split(user_input)
        except ValueError as e:
            console.print(tr("shell.invalid_input", error=e))
            continue

        # Allow user to type full command with 'tenderx' prefix
        if args and args[0] == "tenderx":
            args = args[1:]

        if not args:
            continue

        _run_command(args)

    _in_shell = False
    console.print(f"[dim]{tr('shell.goodbye')}[/dim]\n")


def _entry_point() -> None:
    """Entry point for the tenderx command.

    No arguments: start the interactive shell.
    With arguments: run as a standard CLI command.
    """
    if len(sys.argv) <= 1:
        interactive_shell()
    else:
        from src.i18n import load_locale
        load_locale()
        app()


# --- Command groups ---
ingest_app = typer.Typer(help=tr("help.group.ingest"))
search_app = typer.Typer(help=tr("help.group.search"))
orgs_app = typer.Typer(help=tr("help.group.orgs"))
docs_app = typer.Typer(help=tr("help.group.docs"))
tender_app = typer.Typer(help=tr("help.group.tender"))

app.add_typer(ingest_app, name="ingest")
app.add_typer(search_app, name="search")
app.add_typer(orgs_app, name="orgs")
app.add_typer(docs_app, name="docs")
app.add_typer(tender_app, name="tender")


# ============================================================
# INGEST commands
# ============================================================

@ingest_app.command("run", help=tr("help.cmd.ingest_run"))
def ingest_run(
    days: int = typer.Option(7, help=tr("help.opt.days")),
    date_str: str = typer.Option(None, "--date", help=tr("help.opt.date")),
    enrich: bool = typer.Option(True, help=tr("help.opt.enrich")),
    enrich_bg: bool = typer.Option(False, "--enrich-bg", help=tr("help.opt.enrich_bg")),
) -> None:
    """Ingest tenders from the German procurement API."""
    from src.ingestion.tender_pipeline import TenderPipeline

    async def _run() -> None:
        pipeline = TenderPipeline()
        if date_str:
            target = date.fromisoformat(date_str)
            console.print(tr("ingest.progress_date", date=target))
            result = await pipeline.run_date(target)
        else:
            console.print(tr("ingest.progress_days", days=days))
            result = await pipeline.run(days=days)

        console.print(
            tr("ingest.done",
               fetched=result.total_fetched,
               inserted=result.inserted,
               updated=result.updated,
               errors=result.errors,
               duration=f"{result.duration_seconds:.1f}")
        )

        # If --enrich-bg, spawn background enrichment job instead of inline
        if enrich_bg:
            from src.background.manager import BackgroundJobManager
            manager = BackgroundJobManager()
            job_id = await manager.create_job("enrichment", {})
            manager.spawn_worker(job_id)
            short_id = str(job_id)[:8]
            console.print(tr("bg.enrich_started_bg", job_id=short_id))
            return

        if enrich:
            try:
                from src.ingestion.enrichment import EnrichmentPipeline
                from src.ai.llm_client import OllamaClient

                client = OllamaClient()
                if await client.is_available():
                    console.print(tr("ingest.enrichment_running"))
                    ep = EnrichmentPipeline(client)
                    er = await ep.run()
                    console.print(
                        tr("ingest.enrichment_result",
                           succeeded=er.succeeded,
                           failed=er.failed,
                           skipped=er.skipped)
                    )
                else:
                    console.print(tr("ingest.ollama_unavailable"))
            except Exception as exc:
                console.print(tr("ingest.enrichment_skipped", error=exc))

            # Generate embeddings for enriched tenders
            try:
                from src.search.embeddings import generate_tender_embeddings

                console.print(tr("ingest.embeddings_running"))
                count = await generate_tender_embeddings(limit=500)
                console.print(tr("ingest.embeddings_result", count=count))
            except Exception as exc:
                console.print(tr("ingest.embeddings_skipped", error=exc))

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print(tr("common.db_unavailable"))
    except Exception as exc:
        console.print(tr("common.error", error=exc))


@ingest_app.command("enrich", help=tr("help.cmd.ingest_enrich"))
def ingest_enrich(
    bg: bool = typer.Option(False, "--bg", help=tr("help.opt.bg")),
) -> None:
    """Run AI enrichment on unenriched tenders."""
    if bg:
        async def _bg() -> None:
            from src.background.manager import BackgroundJobManager
            manager = BackgroundJobManager()
            job_id = await manager.create_job("enrichment", {})
            manager.spawn_worker(job_id)
            short_id = str(job_id)[:8]
            console.print(tr("bg.job_started", job_id=short_id))

        try:
            asyncio.run(_bg())
        except Exception as exc:
            console.print(tr("common.error", error=exc))
        return

    async def _run() -> None:
        from src.ingestion.enrichment import EnrichmentPipeline
        from src.ai.llm_client import OllamaClient

        client = OllamaClient()
        if not await client.is_available():
            console.print(tr("ingest.enrich_ollama_unavailable"))
            return

        console.print(tr("ingest.enrich_running"))
        ep = EnrichmentPipeline(client)
        result = await ep.run()
        console.print(
            tr("ingest.enrich_done",
               succeeded=result.succeeded,
               failed=result.failed,
               skipped=result.skipped,
               duration=f"{result.duration_seconds:.1f}")
        )

    try:
        asyncio.run(_run())
    except Exception as exc:
        console.print(tr("common.error", error=exc))


# ============================================================
# SEARCH commands
# ============================================================

@search_app.command("query", help=tr("help.cmd.search_query"))
def search_query(
    query_text: str = typer.Argument(None, help=tr("help.opt.query_text")),
    cpv: str = typer.Option(None, help=tr("help.opt.cpv")),
    nuts: str = typer.Option(None, help=tr("help.opt.nuts")),
    min_value: float = typer.Option(None, help=tr("help.opt.min_value")),
    max_value: float = typer.Option(None, help=tr("help.opt.max_value")),
    limit: int = typer.Option(20, help=tr("help.opt.limit")),
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
            console.print(tr("search.no_results"))
            return

        table = Table(title=tr("search.table_title", count=len(results)))
        table.add_column(tr("search.col_score"), width=6)
        table.add_column(tr("search.col_title"), max_width=60)
        table.add_column(tr("search.col_cpv"), width=12)
        table.add_column(tr("search.col_value"), width=15)
        table.add_column(tr("search.col_deadline"), width=12)

        for r in results:
            tender = r.tender
            score = f"{r.semantic_score:.3f}" if r.semantic_score else "-"
            cpv_str = ", ".join((tender.cpv_codes or [])[:2])
            value = f"{tender.estimated_value:,.0f} {tender.currency}" if tender.estimated_value else "-"
            deadline = tender.submission_deadline.strftime("%Y-%m-%d") if tender.submission_deadline else "-"
            table.add_row(score, tender.title[:60], cpv_str, value, deadline)

        console.print(table)

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print(tr("common.db_unavailable"))
    except Exception as exc:
        console.print(tr("common.error", error=exc))


# ============================================================
# ORGS commands
# ============================================================

@orgs_app.command("load", help=tr("help.cmd.orgs_load"))
def orgs_load(
    csv_path: str = typer.Option("organizations.csv", "--csv", help=tr("help.opt.csv_path")),
) -> None:
    """Load organizations from a CSV file."""
    from pathlib import Path

    # Resolve relative paths against project root (where cli.py lives)
    resolved = Path(csv_path)
    if not resolved.is_absolute():
        resolved = Path(__file__).resolve().parent / csv_path

    async def _run() -> None:
        from src.organizations.csv_loader import OrganizationCSVLoader

        loader = OrganizationCSVLoader()
        result = await loader.load(resolved)

        console.print(
            tr("orgs.load_done",
               total=result.total_rows,
               inserted=result.inserted,
               updated=result.updated,
               skipped=result.skipped)
        )
        if result.errors:
            console.print(tr("orgs.load_errors", count=len(result.errors)))
            for err in result.errors[:10]:
                console.print(f"  {err}")

    try:
        asyncio.run(_run())
    except FileNotFoundError:
        console.print(tr("orgs.file_not_found", path=str(resolved)))
    except ConnectionRefusedError:
        console.print(tr("common.db_unavailable"))
    except Exception as exc:
        console.print(tr("common.error", error=exc))


@orgs_app.command("match", help=tr("help.cmd.orgs_match"))
def orgs_match(
    org_id: str = typer.Option(None, "--org-id", help=tr("help.opt.org_id")),
    all_orgs: bool = typer.Option(False, "--all", help=tr("help.opt.all_orgs")),
) -> None:
    """Run tender matching for organizations."""
    if not org_id and not all_orgs:
        console.print(tr("orgs.match_specify"))
        raise typer.Exit(1)

    async def _run() -> None:
        from uuid import UUID
        from src.matching.matcher import TenderMatcher

        matcher = TenderMatcher()

        if all_orgs:
            console.print(tr("orgs.match_all_progress"))
            results = await matcher.match_all()
            table = Table(title=tr("orgs.match_table_title", count=len(results)))
            table.add_column(tr("orgs.match_col_organization"))
            table.add_column(tr("orgs.match_col_queries"))
            table.add_column(tr("orgs.match_col_matches"))
            table.add_column(tr("orgs.match_col_source"))
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
            console.print(tr("orgs.match_one_progress", uid=uid))
            result = await matcher.match_organization(uid)
            console.print(tr("orgs.match_one_org", name=result.organization_name))
            console.print(tr("orgs.match_one_source", source=result.query_source))
            console.print(tr("orgs.match_one_queries"))
            for q in result.queries:
                console.print(f"  - {q}")
            console.print(tr("orgs.match_one_total", count=result.total_matches))
            if result.top_matches:
                console.print(tr("orgs.match_one_top"))
                for title, score in result.top_matches[:10]:
                    console.print(f"  {score:.3f} — {title[:70]}")

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print(tr("common.db_unavailable"))
    except Exception as exc:
        console.print(tr("common.error", error=exc))


# ============================================================
# DOCS commands
# ============================================================

@docs_app.command("analyze", help=tr("help.cmd.docs_analyze"))
def docs_analyze() -> None:
    """Analyze document supplier portals."""
    async def _run() -> None:
        from pathlib import Path
        from src.documents.analyzer import SupplierAnalyzer

        analyzer = SupplierAnalyzer()
        stats = await analyzer.analyze()

        if not stats:
            console.print(tr("docs.no_portals"))
            return

        table = Table(title=tr("docs.analyze_title"))
        table.add_column(tr("docs.col_domain"))
        table.add_column(tr("docs.col_tenders"), justify="right")
        table.add_column(tr("docs.col_percent"), justify="right")
        for s in stats[:20]:
            table.add_row(s.domain, str(s.tender_count), f"{s.percentage:.1f}%")
        console.print(table)

        out = Path("data/output/supplier_analysis.csv")
        analyzer.export_csv(stats, out)
        console.print(tr("docs.csv_saved", path=out))

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print(tr("common.db_unavailable"))
    except Exception as exc:
        console.print(tr("common.error", error=exc))


@docs_app.command("download", help=tr("help.cmd.docs_download"))
def docs_download(
    supplier: str = typer.Option(..., help=tr("help.opt.supplier")),
    limit: int = typer.Option(100, help=tr("help.opt.limit")),
    bg: bool = typer.Option(False, "--bg", help=tr("help.opt.bg")),
) -> None:
    """Download documents from a supplier portal."""
    if bg:
        async def _bg() -> None:
            from src.background.manager import BackgroundJobManager
            manager = BackgroundJobManager()
            job_id = await manager.create_job(
                "docs_download", {"domain": supplier, "limit": limit}
            )
            manager.spawn_worker(job_id)
            short_id = str(job_id)[:8]
            console.print(tr("bg.job_started", job_id=short_id))

        try:
            asyncio.run(_bg())
        except Exception as exc:
            console.print(tr("common.error", error=exc))
        return

    async def _run() -> None:
        from src.documents.downloader import DocumentDownloader

        dl = DocumentDownloader()
        result = await dl.download_for_supplier(supplier, limit=limit)
        console.print(
            tr("docs.download_done",
               tenders=result.tenders_processed,
               downloaded=result.documents_downloaded,
               failed=result.documents_failed,
               bytes=f"{result.total_bytes:,}")
        )

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print(tr("common.db_unavailable"))
    except Exception as exc:
        console.print(tr("common.error", error=exc))


# ============================================================
# TENDER commands
# ============================================================

@tender_app.command("show", help=tr("help.cmd.tender_show"))
def tender_show(
    tender_id: str = typer.Argument(help=tr("help.opt.tender_id")),
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
            console.print(tr("tender.not_found", id=tender_id))
            return

        lines = [
            f"[bold]{tr('tender.label_contract')}[/bold] {tender.contract_number or '-'}",
            f"[bold]{tr('tender.label_type')}[/bold] {tender.contract_type or '-'}",
            f"[bold]{tr('tender.label_value')}[/bold] {tender.estimated_value or '-'} {tender.currency}",
            f"[bold]{tr('tender.label_published')}[/bold] {tender.publication_date or '-'}",
            f"[bold]{tr('tender.label_deadline')}[/bold] {tender.submission_deadline or '-'}",
            f"[bold]{tr('tender.label_location')}[/bold] {tender.execution_location or '-'}",
            f"[bold]{tr('tender.label_cpv')}[/bold] {', '.join(tender.cpv_codes or [])}",
            f"[bold]{tr('tender.label_nuts')}[/bold] {', '.join(tender.nuts_codes or [])}",
            f"[bold]{tr('tender.label_platform')}[/bold] {tender.platform_url or '-'}",
            f"[bold]{tr('tender.label_docs_portal')}[/bold] {tender.document_portal_url or '-'}",
        ]

        if tender.ai_summary:
            lines.append(f"\n[bold]{tr('tender.label_ai_summary')}[/bold] {tender.ai_summary}")

        if tender.issuer:
            lines.append(f"\n[bold]{tr('tender.label_issuer')}[/bold] {tender.issuer.name}")
            if tender.issuer.contact_email:
                lines.append(f"[bold]{tr('tender.label_contact')}[/bold] {tender.issuer.contact_email}")

        if tender.lots:
            lines.append(f"\n[bold]{tr('tender.label_lots', count=len(tender.lots))}[/bold]")
            for lot in tender.lots:
                val = f" — {lot.estimated_value} EUR" if lot.estimated_value else ""
                lines.append(f"  {lot.lot_number}. {lot.title or tr('tender.untitled')}{val}")

        if tender.documents:
            lines.append(f"\n[bold]{tr('tender.label_documents', count=len(tender.documents))}[/bold]")
            for doc in tender.documents:
                lines.append(f"  - {doc.filename} ({doc.content_type or tr('tender.unknown_type')})")

        console.print(
            Panel("\n".join(lines), title=tender.title[:80], expand=False)
        )

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print(tr("common.db_unavailable"))
    except Exception as exc:
        console.print(tr("common.error", error=exc))


# ============================================================
# DASHBOARD command
# ============================================================

def _format_duration(start: datetime | None, end: datetime | None) -> str:
    """Format a duration between two datetimes as a human-readable string."""
    if not start:
        return "-"
    ref = end or datetime.now(timezone.utc)
    # Make both timezone-aware or naive for subtraction
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    delta = ref - start
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60}s"
    return f"{secs // 3600}h {(secs % 3600) // 60}m"


def _progress_bar(current: int, total: int | None) -> str:
    """Build a text-based progress bar."""
    if not total or total == 0:
        return f"{current}/?"
    pct = current / total
    filled = int(pct * 20)
    bar = "=" * filled + ">" + " " * (19 - filled) if filled < 20 else "=" * 20
    return f"[{bar}] {current}/{total}"


def _status_style(status: str) -> str:
    """Return Rich markup color for a job status."""
    styles = {
        "pending": "yellow",
        "running": "bright_blue",
        "completed": "green",
        "failed": "red",
        "cancelled": "dim",
    }
    color = styles.get(status, "white")
    return f"[{color}]{status}[/{color}]"


def _build_dashboard_table(jobs: list) -> Table:
    """Build a Rich table for the dashboard."""
    job_type_labels = {
        "enrichment": tr("bg.job_type_enrichment"),
        "docs_download": tr("bg.job_type_docs_download"),
    }

    table = Table(title=tr("dashboard.title"), expand=True)
    table.add_column(tr("dashboard.col_id"), width=10)
    table.add_column(tr("dashboard.col_type"), width=18)
    table.add_column(tr("dashboard.col_status"), width=12)
    table.add_column(tr("dashboard.col_progress"), width=28)
    table.add_column(tr("dashboard.col_duration"), width=10)
    table.add_column(tr("dashboard.col_errors"), width=8)

    for job in jobs:
        short_id = str(job.id)[:8]
        job_label = job_type_labels.get(job.job_type, job.job_type)
        status = _status_style(job.status)
        progress = _progress_bar(job.progress_current, job.progress_total)
        duration = _format_duration(job.started_at, job.completed_at)

        # Extract error count from result_summary if available
        errors = "-"
        if job.result_summary and isinstance(job.result_summary, dict):
            err_count = job.result_summary.get("failed", job.result_summary.get("documents_failed"))
            if err_count is not None:
                errors = str(err_count)
        if job.error_message:
            errors = "[red]1[/red]"

        table.add_row(short_id, job_label, status, progress, duration, errors)

    return table


@app.command("dashboard", help=tr("help.cmd.dashboard"))
def dashboard() -> None:
    """Monitor background jobs in real time."""
    async def _get_jobs() -> list:
        from src.background.manager import BackgroundJobManager
        manager = BackgroundJobManager()
        stale = await manager.cleanup_stale()
        if stale:
            console.print(tr("dashboard.stale_detected", count=stale))
        return await manager.list_jobs()

    try:
        jobs = asyncio.run(_get_jobs())
    except ConnectionRefusedError:
        console.print(tr("common.db_unavailable"))
        return
    except Exception as exc:
        console.print(tr("common.error", error=exc))
        return

    if not jobs:
        console.print(tr("dashboard.no_jobs"))
        return

    # Check if any active jobs exist for live mode
    has_active = any(j.status in ("pending", "running") for j in jobs)

    if not has_active:
        # Static display if no active jobs
        console.print(_build_dashboard_table(jobs))
        return

    # Live refresh mode
    console.print(tr("dashboard.exit_hint"))
    try:
        with Live(console=console, refresh_per_second=0.7) as live:
            while True:
                from src.db.session import reset_engine
                reset_engine()
                jobs = asyncio.run(_get_jobs())
                live.update(_build_dashboard_table(jobs))

                has_active = any(j.status in ("pending", "running") for j in jobs)
                if not has_active:
                    break
                time.sleep(1.5)
    except KeyboardInterrupt:
        console.print()


# ============================================================
# STATS command
# ============================================================

@app.command("stats", help=tr("help.cmd.stats"))
def stats(
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help=tr("help.opt.verbose"),
    ),
) -> None:
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

        pct_enrich = f"{enriched/tender_count*100:.0f}%" if tender_count else "0%"
        pct_embed = f"{embedded/tender_count*100:.0f}%" if tender_count else "0%"

        if verbose:
            table = Table(
                title=tr("stats.table_title_detailed"),
                show_lines=True,
            )
            table.add_column(tr("stats.col_metric"), style="bold", min_width=20)
            table.add_column(tr("stats.col_value"), justify="right", min_width=12)
            table.add_column(tr("stats.col_description"), style="dim", min_width=40)

            table.add_row(tr("stats.metric_tenders"), f"{tender_count:,}", tr("stats.desc_tenders"))
            table.add_row(tr("stats.metric_issuers"), f"{issuer_count:,}", tr("stats.desc_issuers"))
            table.add_row(tr("stats.metric_orgs"), f"{org_count:,}", tr("stats.desc_orgs"))
            table.add_row(tr("stats.metric_docs"), f"{doc_count:,}", tr("stats.desc_docs"))
            table.add_row(tr("stats.metric_matches"), f"{match_count:,}", tr("stats.desc_matches"))
            table.add_row(
                tr("stats.metric_date_range"),
                f"{min_date or '-'} to {max_date or '-'}",
                tr("stats.desc_date_range"),
            )
            table.add_row(
                tr("stats.metric_enriched"),
                f"{enriched:,} / {tender_count:,} ({pct_enrich})",
                tr("stats.desc_enriched"),
            )
            table.add_row(
                tr("stats.metric_embedded"),
                f"{embedded:,} / {tender_count:,} ({pct_embed})",
                tr("stats.desc_embedded"),
            )
        else:
            table = Table(title=tr("stats.table_title"))
            table.add_column(tr("stats.col_metric"), style="bold")
            table.add_column(tr("stats.col_value"), justify="right")

            table.add_row(tr("stats.metric_tenders"), f"{tender_count:,}")
            table.add_row(tr("stats.metric_issuers"), f"{issuer_count:,}")
            table.add_row(tr("stats.metric_orgs"), f"{org_count:,}")
            table.add_row(tr("stats.metric_docs"), f"{doc_count:,}")
            table.add_row(tr("stats.metric_matches"), f"{match_count:,}")
            table.add_row(tr("stats.metric_date_range"), f"{min_date or '-'} to {max_date or '-'}")
            table.add_row(tr("stats.metric_enriched"), f"{enriched:,} / {tender_count:,} ({pct_enrich})")
            table.add_row(tr("stats.metric_embedded"), f"{embedded:,} / {tender_count:,} ({pct_embed})")

        console.print(table)

        if not verbose:
            console.print(tr("stats.tip"))

    try:
        asyncio.run(_run())
    except ConnectionRefusedError:
        console.print(tr("common.db_unavailable"))
    except Exception as exc:
        console.print(tr("common.error", error=exc))


# ============================================================
# LANG command
# ============================================================

@app.command("lang", help=tr("help.cmd.lang"))
def lang_cmd(
    default: bool = typer.Option(
        False, "--default", "-d",
        help=tr("help.opt.lang_default"),
    ),
) -> None:
    """Change the CLI language / Alterar idioma / Sprache ändern."""
    from src.i18n import get_locale, save_locale, set_locale, SUPPORTED_LOCALES, load_locale

    load_locale()

    if default:
        save_locale("en-US")
        set_locale("en-US")
        console.print(tr("lang.reset_to_default"))
        return

    # Show current language
    current = get_locale()
    console.print(tr("lang.current", lang=SUPPORTED_LOCALES[current], code=current))
    console.print()

    # Re-display the language selection menu (forced)
    _show_language_menu(force=True)


# ============================================================
# PURGE command
# ============================================================

@app.command("purge", help=tr("help.cmd.purge"))
def purge(
    yes: bool = typer.Option(False, "--yes", "-y", help=tr("help.opt.yes")),
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
                "background_jobs",
            ]
            for tbl in tables:
                await session.execute(text(f"TRUNCATE TABLE {tbl} CASCADE"))
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

        console.print(tr("purge.header"))

        table = Table(title=tr("purge.db_table_title"), show_lines=False)
        table.add_column(tr("purge.col_table"), style="bold")
        table.add_column(tr("purge.col_rows"), justify="right")
        table.add_row(tr("purge.row_tenders"), f"{counts['tenders']:,}")
        table.add_row(tr("purge.row_with_summaries"), f"{counts['enriched_tenders']:,}")
        table.add_row(tr("purge.row_with_embeddings"), f"{counts['embedded_vectors']:,}")
        table.add_row(tr("purge.row_issuers"), f"{counts['issuers']:,}")
        table.add_row(tr("purge.row_organizations"), f"{counts['organizations']:,}")
        table.add_row(tr("purge.row_tender_lots"), f"{counts['tender_lots']:,}")
        table.add_row(tr("purge.row_tender_documents"), f"{counts['tender_documents']:,}")
        table.add_row(tr("purge.row_match_results"), f"{counts['match_results']:,}")
        table.add_row(tr("purge.total_rows"), f"[bold]{total_rows:,}[/bold]")
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
        console.print(tr("purge.minio_bucket", bucket=_settings.minio_bucket, count=minio_count))

        # Generated files
        output_dir = Path("data/output")
        gen_files = [
            f for f in output_dir.iterdir() if f.name != ".gitkeep"
        ] if output_dir.exists() else []
        if gen_files:
            console.print(tr("purge.gen_files_header"))
            for f in gen_files:
                size_kb = f.stat().st_size / 1024
                console.print(f"  - {f.name} ({size_kb:.1f} KB)")
        else:
            console.print(tr("purge.gen_files_none"))

        return total_rows, minio_count, gen_files

    try:
        # Step 1: Gather what will be deleted (async — first event loop)
        counts = asyncio.run(_count_and_purge(do_purge=False))

        # Step 2: Show summary (sync — no event loop needed)
        total_rows, minio_count, gen_files = _show_summary(counts)

        # Nothing to delete?
        if total_rows == 0 and minio_count == 0 and not gen_files:
            console.print(tr("purge.nothing_to_purge"))
            return

        # Step 3: Ask for confirmation (sync)
        if not yes:
            console.print("")
            confirm = typer.confirm(
                tr("purge.confirm"),
                default=False,
            )
            if not confirm:
                console.print(tr("purge.aborted"))
                raise typer.Exit(0)

        # Step 4: Execute purge
        console.print(tr("purge.purging"))

        # Database (async — second event loop, need fresh engine)
        if total_rows > 0:
            console.print(tr("purge.truncating_db"), end=" ")
            from src.db.session import reset_engine
            reset_engine()  # dispose old engine bound to closed event loop
            asyncio.run(_count_and_purge(do_purge=True))
            console.print(tr("purge.truncating_db_ok", count=f"{total_rows:,}"))

        # MinIO (sync)
        if minio_count > 0:
            console.print(tr("purge.removing_minio"), end=" ")
            deleted_count = _purge_minio()
            console.print(tr("purge.removing_minio_ok", count=deleted_count))

        # Files (sync)
        if gen_files:
            console.print(tr("purge.deleting_files"), end=" ")
            deleted_files = _purge_files()
            console.print(tr("purge.deleting_files_ok", count=len(deleted_files)))

        console.print(tr("purge.complete"))

    except ConnectionRefusedError:
        console.print(tr("common.db_unavailable"))
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(tr("common.error", error=exc))


if __name__ == "__main__":
    _entry_point()
