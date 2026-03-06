"""German (de-DE) translation strings.

Every other locale file must mirror exactly the same keys.
Rich markup ([green], [bold], etc.) is embedded in values.
Format placeholders use Python .format() syntax: {name}.
"""

STRINGS: dict[str, str] = {
    # ── Welcome Screen ─────────────────────────────────────────
    "welcome.tagline": "Deutsche Vergabe-Intelligenzplattform",
    "welcome.quick_start": "Schnellstart",
    "welcome.menu.ingest_run": "Ausschreibungen von der Vergabe-API einlesen",
    "welcome.menu.ingest_enrich": "KI-Anreicherung gespeicherter Ausschreibungen starten",
    "welcome.menu.ingest_embed": "Vektor-Embeddings fuer die Suche generieren",
    "welcome.menu.search_query": "Semantische + strukturierte Ausschreibungssuche",
    "welcome.menu.orgs_load": "Organisationen aus CSV laden",
    "welcome.menu.orgs_list": "Alle Organisationen und Details auflisten",
    "welcome.menu.orgs_match": "Organisationen mit passenden Ausschreibungen abgleichen",
    "welcome.menu.stats": "Systemstatistiken anzeigen",
    "welcome.menu.docs_analyze": "Dokumenten-Lieferantenportale analysieren",
    "welcome.menu.docs_download": "Dokumente vom Lieferantenportal herunterladen",
    "welcome.menu.dashboard": "Hintergrundjobs in Echtzeit ueberwachen",
    "welcome.menu.tender_list": "Gespeicherte Ausschreibungen auflisten und pruefen",
    "welcome.menu.kill": "Hintergrundjobs abbrechen",
    "welcome.menu.lang": "CLI-Sprache aendern",
    "welcome.menu.purge": "ALLE Daten loeschen (DB + MinIO + Dateien)",
    "welcome.help_desc": "Alle Befehle und detaillierte Nutzung anzeigen",

    # ── Detailed help (tenderx help) ────────────────────────────
    "help.detailed.title": "TenderX — Befehlsreferenz",
    "help.detailed.section_ingest": "Datenaufnahme",
    "help.detailed.section_search": "Suche",
    "help.detailed.section_orgs": "Organisationen",
    "help.detailed.section_docs": "Dokumente",
    "help.detailed.section_tender": "Ausschreibungen",
    "help.detailed.section_system": "System",
    "help.detailed.footer": "[dim]Tipp: Fuehren Sie einen Befehl mit --help aus fuer vollstaendige Details (z.B. tenderx ingest run --help)[/dim]",

    # ── Interactive Shell ──────────────────────────────────────
    "shell.hint": "Geben Sie 'help' fuer Befehle oder 'exit' zum Beenden ein.",
    "shell.interrupted": "Unterbrochen.",
    "shell.goodbye": "Auf Wiedersehen!",
    "shell.invalid_input": "[red]Ungueltige Eingabe: {error}[/red]",

    # ── Help texts — app & groups ──────────────────────────────
    "help.app": "Deutsche Vergabe-Intelligenzplattform",
    "help.group.ingest": "Befehle zur Ausschreibungserfassung",
    "help.group.search": "Ausschreibungen suchen und filtern",
    "help.group.orgs": "Organisationsverwaltung",
    "help.group.docs": "Befehle zur Dokumentenverwaltung",
    "help.group.tender": "Befehle zur Ausschreibungsansicht",

    # ── Help texts — commands ──────────────────────────────────
    "help.cmd.ingest_run": "Ausschreibungen von der deutschen Vergabe-API einlesen.",
    "help.cmd.ingest_enrich": "KI-Anreicherung fuer nicht angereicherte Ausschreibungen starten.",
    "help.cmd.ingest_embed": "Vektor-Embeddings fuer angereicherte Ausschreibungen generieren.",
    "help.cmd.dashboard": "Hintergrundjobs in Echtzeit ueberwachen. Zeigt eine Live-Tabelle mit Fortschrittsbalken aller Jobs. Mit --inspect <job-id> einzelne Jobs inspizieren.",
    "help.cmd.search_query": "Ausschreibungen mit semantischen und strukturierten Filtern suchen.",
    "help.cmd.orgs_load": "Organisationen aus einer CSV-Datei laden.",
    "help.cmd.orgs_list": "Alle Organisationen mit Details auflisten.",
    "help.cmd.orgs_match": "Ausschreibungsabgleich fuer Organisationen durchfuehren.",
    "help.cmd.docs_analyze": "Dokumenten-Lieferantenportale analysieren.",
    "help.cmd.docs_download": "Dokumente von einem Lieferantenportal herunterladen.",
    "help.cmd.tender_list": "Ausschreibungen mit optionalen Filtern auflisten.",
    "help.cmd.tender_show": "Detailinformationen zu einer Ausschreibung anzeigen.",
    "help.cmd.stats": "Systemstatistiken anzeigen.",
    "help.cmd.purge": "ALLE Daten loeschen: Datenbankeintraege, MinIO-Objekte und generierte Dateien.",
    "help.cmd.lang": "CLI-Sprache aendern.",

    # ── Help texts — options ───────────────────────────────────
    "help.opt.days": "Anzahl der Tage fuer die Erfassung",
    "help.opt.date": "Bestimmtes Datum (JJJJ-MM-TT)",
    "help.opt.enrich": "KI-Anreicherung nach der Erfassung starten",
    "help.opt.query_text": "Freitext-Suchanfrage",
    "help.opt.cpv": "CPV-Code-Filter",
    "help.opt.nuts": "NUTS-Code-Filter",
    "help.opt.min_value": "Minimaler Schaetzwert",
    "help.opt.max_value": "Maximaler Schaetzwert",
    "help.opt.limit": "Maximale Ergebnisse",
    "help.opt.csv_path": "Pfad zur Organisations-CSV",
    "help.opt.org_id": "Bestimmte Organisation per UUID abgleichen",
    "help.opt.all_orgs": "Alle Organisationen abgleichen",
    "help.opt.supplier": "Lieferanten-Domain zum Herunterladen",
    "help.opt.tender_id": "Ausschreibungs-UUID",
    "help.opt.verbose": "Detaillierte Beschreibungen fuer jede Metrik anzeigen",
    "help.opt.yes": "Bestaetigungsabfrage ueberspringen",
    "help.opt.enriched_only": "Nur angereicherte Ausschreibungen anzeigen (mit KI-Zusammenfassung)",
    "help.opt.lang_default": "Sprache auf Englisch (Standard) zuruecksetzen",
    "help.opt.bg": "Im Hintergrund ausfuehren (ueberlebt CLI-Beendigung, ueberwachen mit 'tenderx dashboard')",
    "help.opt.enrich_bg": "KI-Anreicherung nach Erfassung im Hintergrund starten",
    "help.opt.gpu": "GPU-beschleunigte parallele Anreicherung aktivieren (10 gleichzeitig, erfordert NVIDIA GPU)",
    "help.opt.enrich_all": "ALLE Tenders erneut anreichern (einschliesslich bereits angereicherter)",
    "help.opt.archive": "Rohe API-Exporte in MinIO archivieren (Standard: aktiviert)",
    "help.opt.has_website": "Nur Organisationen mit Website anzeigen",
    "help.opt.no_website": "Nur Organisationen ohne Website anzeigen",

    # ── Ingest ─────────────────────────────────────────────────
    "ingest.progress_date": "Ausschreibungen fuer {date} werden eingelesen...",
    "ingest.progress_days": "Ausschreibungen der letzten {days} Tage werden eingelesen...",
    "ingest.done": (
        "\n[green]Fertig![/green] "
        "{fetched} abgerufen, {inserted} neu, {updated} aktualisiert, "
        "{errors} Fehler ({duration}s)"
    ),
    "ingest.enrichment_running": "\nKI-Anreicherung wird ausgefuehrt...",
    "ingest.enrichment_result": (
        "[green]Anreicherung:[/green] "
        "{succeeded} angereichert, {failed} fehlgeschlagen, {skipped} uebersprungen"
    ),
    "ingest.ollama_unavailable": "[yellow]Ollama nicht verfuegbar \u2014 Anreicherung wird uebersprungen[/yellow]",
    "ingest.enrichment_skipped": "[yellow]Anreicherung uebersprungen: {error}[/yellow]",
    "ingest.ocds_enriching": "Dokument-URLs aus OCDS anreichern...",
    "ingest.ocds_result": "[green]OCDS:[/green] {updated} URLs angereichert, {not_found} nicht gefunden",
    "ingest.ocds_skipped": "[dim]OCDS-Anreicherung: keine Daten verfuegbar[/dim]",
    "ingest.archived_export": "[dim]{fmt} fuer {date} archiviert[/dim]",
    "ingest.archive_skipped": "[dim]Export-Archivierung deaktiviert[/dim]",
    "ingest.embeddings_running": "\nEmbeddings werden generiert...",
    "ingest.embeddings_result": "[green]Embeddings:[/green] {count} generiert",
    "ingest.embeddings_skipped": "[yellow]Embeddings uebersprungen: {error}[/yellow]",

    # ── Ingest — enrich subcommand ─────────────────────────────
    "ingest.enrich_ollama_unavailable": "[red]Ollama nicht verfuegbar. Bitte zuerst starten.[/red]",
    "ingest.enrich_running": "KI-Anreicherung wird ausgefuehrt...",
    "ingest.enrich_done": (
        "[green]Fertig![/green] "
        "{succeeded} angereichert, {failed} fehlgeschlagen, {skipped} uebersprungen ({duration}s)"
    ),

    # ── Search ─────────────────────────────────────────────────
    "search.no_results": "[yellow]Keine Ergebnisse gefunden.[/yellow]",
    "search.table_title": "Suchergebnisse ({count})",
    "search.col_id": "ID",
    "search.col_score": "Punktzahl",
    "search.col_title": "Titel",
    "search.col_cpv": "CPV",
    "search.col_value": "Wert",
    "search.col_deadline": "Frist",

    # ── Organizations ──────────────────────────────────────────
    "orgs.load_done": (
        "\n[green]Fertig![/green] "
        "{total} gesamt, {inserted} neu, {updated} aktualisiert, {skipped} uebersprungen"
    ),
    "orgs.load_errors": "[yellow]Fehler ({count}):[/yellow]",
    "orgs.file_not_found": "[red]Datei nicht gefunden: {path}[/red]",
    "orgs.match_specify": "[red]Bitte --org-id oder --all angeben[/red]",
    "orgs.match_all_progress": "Alle Organisationen werden abgeglichen...",
    "orgs.match_table_title": "Abgleichergebnisse ({count})",
    "orgs.match_col_organization": "Organisation",
    "orgs.match_col_queries": "Anfragen",
    "orgs.match_col_matches": "Treffer",
    "orgs.match_col_source": "Quelle",
    "orgs.match_one_progress": "Organisation {uid} wird abgeglichen...",
    "orgs.match_one_org": "\nOrganisation: [bold]{name}[/bold]",
    "orgs.match_one_source": "Anfragequelle: {source}",
    "orgs.match_one_queries": "\nAnfragen:",
    "orgs.match_one_total": "\nTreffer gesamt: {count}",
    "orgs.match_one_top": "\nBeste Treffer:",
    "orgs.list_title": "Organisationen ({count})",
    "orgs.list_no_results": "[dim]Keine Organisationen gefunden.[/dim]",
    "orgs.col_id": "ID",
    "orgs.col_name": "Name",
    "orgs.col_tax_id": "Steuer-ID",
    "orgs.col_website": "Website",
    "orgs.col_description": "Beschreibung",
    "orgs.col_keywords": "Schlagwoerter",
    "orgs.col_resolved": "Aufgeloest",

    # ── Documents ──────────────────────────────────────────────
    "docs.no_portals": "[yellow]Keine Dokumentenportal-URLs gefunden.[/yellow]",
    "docs.analyze_title": "Dokumenten-Lieferantenanalyse",
    "docs.col_domain": "Domain",
    "docs.col_tenders": "Ausschreibungen",
    "docs.col_percent": "%",
    "docs.csv_saved": "\n[green]CSV gespeichert unter {path}[/green]",
    "docs.download_done": (
        "\n[green]Fertig![/green] "
        "{tenders} Ausschreibungen, {downloaded} heruntergeladen, "
        "{failed} fehlgeschlagen, {no_links} ohne Links, {bytes} Bytes"
    ),

    # ── Tender show ────────────────────────────────────────────
    "tender.not_found": "[red]Ausschreibung {id} nicht gefunden.[/red]",
    "tender.label_contract": "Vertrag:",
    "tender.label_type": "Art:",
    "tender.label_value": "Wert:",
    "tender.label_published": "Veroeffentlicht:",
    "tender.label_deadline": "Frist:",
    "tender.label_location": "Ort:",
    "tender.label_cpv": "CPV:",
    "tender.label_nuts": "NUTS:",
    "tender.label_platform": "Plattform:",
    "tender.label_docs_portal": "Dokumentenportal:",
    "tender.label_ai_summary": "KI-Zusammenfassung:",
    "tender.label_embedding": "Embedding:",
    "tender.label_issuer": "Vergabestelle:",
    "tender.label_contact": "Kontakt:",
    "tender.label_lots": "Lose ({count}):",
    "tender.label_documents": "Dokumente ({count}):",
    "tender.list_title": "Ausschreibungen ({count})",
    "tender.untitled": "Ohne Titel",
    "tender.unknown_type": "unbekannt",

    # ── Stats ──────────────────────────────────────────────────
    "stats.table_title": "Systemstatistiken",
    "stats.table_title_detailed": "Systemstatistiken  [dim](detailliert)[/dim]",
    "stats.col_metric": "Metrik",
    "stats.col_value": "Wert",
    "stats.col_description": "Beschreibung",
    "stats.metric_tenders": "Ausschreibungen gesamt",
    "stats.metric_issuers": "Vergabestellen gesamt",
    "stats.metric_orgs": "Organisationen gesamt",
    "stats.metric_docs": "Dokumente gesamt",
    "stats.metric_matches": "Treffer gesamt",
    "stats.metric_date_range": "Zeitraum",
    "stats.metric_enriched": "Angereichert",
    "stats.metric_embedded": "Mit Embedding",
    "stats.desc_tenders": (
        "Oeffentliche Vergabebekanntmachungen, eingelesen von oeffentlichevergabe.de. "
        "Jede Ausschreibung stellt eine Vergabemoeglichkeit dar, die von einer deutschen Behoerde veroeffentlicht wurde."
    ),
    "stats.desc_issuers": (
        "Unterschiedliche Vergabestellen, die Ausschreibungen veroeffentlicht haben. "
        "Umfasst Bundes-, Landes- und Kommunalbehoerden in ganz Deutschland."
    ),
    "stats.desc_orgs": (
        "Unternehmen, die aus der Challenge-CSV geladen wurden. "
        "Diese sind potenzielle Bieter, deren Profile mit verfuegbaren Ausschreibungen abgeglichen werden."
    ),
    "stats.desc_docs": (
        "Vergabeunterlagen (PDF, DOCX usw.), die von Lieferantenportalen heruntergeladen "
        "und in MinIO-Objektspeicher fuer den Offline-Zugriff abgelegt wurden."
    ),
    "stats.desc_matches": (
        "Ergebnisse des KI-Abgleichs zwischen Organisationen und Ausschreibungen. "
        "Jeder Treffer enthaelt einen Aehnlichkeitswert aus der hybriden semantisch-strukturierten Suche."
    ),
    "stats.desc_date_range": (
        "Veroeffentlichungszeitraum der eingelesenen Ausschreibungen. Gibt das Zeitfenster an, "
        "das durch die aktuell in der Datenbank vorhandenen Daten abgedeckt wird."
    ),
    "stats.desc_enriched": (
        "Ausschreibungen, die von Ollama (gemma3:4b) verarbeitet wurden, um eine KI-Zusammenfassung "
        "und durchsuchbaren Text zu generieren. Die Anreicherung verbessert die Suchrelevanz und Lesbarkeit."
    ),
    "stats.desc_embedded": (
        "Ausschreibungen mit einem 384-dimensionalen Vektor-Embedding (paraphrase-multilingual-MiniLM-L12-v2), "
        "gespeichert in pgvector fuer die semantische Aehnlichkeitssuche."
    ),
    "stats.tip": (
        "\n[dim]Tipp: Fuehren Sie [bold]tenderx stats --verbose[/bold] "
        "aus, um detaillierte Beschreibungen jeder Metrik zu erhalten.[/dim]"
    ),

    # ── Purge ──────────────────────────────────────────────────
    "purge.header": "\n[bold red]BEREINIGUNG -- Die folgenden Daten werden DAUERHAFT geloescht:[/bold red]\n",
    "purge.db_table_title": "Datenbanktabellen",
    "purge.col_table": "Tabelle",
    "purge.col_rows": "Zeilen",
    "purge.row_tenders": "tenders",
    "purge.row_with_summaries": "  - mit KI-Zusammenfassungen",
    "purge.row_with_embeddings": "  - mit Embeddings (384-dim Vektoren)",
    "purge.row_issuers": "issuers",
    "purge.row_organizations": "organizations",
    "purge.row_tender_lots": "tender_lots",
    "purge.row_tender_documents": "tender_documents",
    "purge.row_match_results": "match_results",
    "purge.total_rows": "[bold]Zeilen gesamt[/bold]",
    "purge.minio_bucket": "\n[bold]MinIO-Bucket[/bold] ({bucket}): [yellow]{count} Objekte[/yellow]",
    "purge.gen_files_header": "\n[bold]Generierte Dateien[/bold] (data/output/):",
    "purge.gen_files_none": "\n[bold]Generierte Dateien[/bold]: keine",
    "purge.nothing_to_purge": "\n[green]Nichts zu bereinigen -- das System ist bereits sauber.[/green]",
    "purge.confirm": "Sind Sie sicher, dass Sie ALLE oben genannten Daten loeschen moechten? Dies kann nicht rueckgaengig gemacht werden",
    "purge.aborted": "[yellow]Abgebrochen.[/yellow]",
    "purge.purging": "\n[bold]Bereinigung laeuft...[/bold]",
    "purge.truncating_db": "  Datenbanktabellen werden geleert...",
    "purge.truncating_db_ok": "[green]OK[/green] {count} Zeilen geloescht",
    "purge.removing_minio": "  MinIO-Objekte werden entfernt...",
    "purge.removing_minio_ok": "[green]OK[/green] {count} Objekte entfernt",
    "purge.deleting_files": "  Generierte Dateien werden geloescht...",
    "purge.deleting_files_ok": "[green]OK[/green] {count} Dateien geloescht",
    "purge.complete": "\n[bold green]Bereinigung abgeschlossen.[/bold green] Das System ist sauber.\n",

    # ── Dashboard ──────────────────────────────────────────────
    "dashboard.title": "Hintergrundjobs-Dashboard",
    "dashboard.col_id": "ID",
    "dashboard.col_type": "Typ",
    "dashboard.col_status": "Status",
    "dashboard.col_progress": "Fortschritt",
    "dashboard.col_duration": "Dauer",
    "dashboard.col_errors": "Fehler",
    "dashboard.no_jobs": "[dim]Keine Hintergrundjobs gefunden. Starten Sie einen mit der --bg Flag.[/dim]",
    "dashboard.exit_hint": "[dim]Druecken Sie Strg+C zum Beenden[/dim]",
    "dashboard.stale_detected": "[yellow]{count} veraltete(r) Job(s) erkannt — als fehlgeschlagen markiert.[/yellow]",
    "dashboard.inspect_title": "Job inspizieren {job_id}",
    "dashboard.inspect_not_found": "[red]Job {job_id} nicht gefunden.[/red]",
    "dashboard.inspect_status": "Status: {status}  |  Fortschritt: {progress}  |  Dauer: {duration}",
    "dashboard.inspect_log_title": "Worker-Log (letzte {lines} Zeilen)",
    "dashboard.inspect_tenders_title": "Fortschritt pro Tender",
    "dashboard.inspect_no_state": "[dim]Kein Pro-Tender-Status verfuegbar (sequentieller Modus oder Job noch nicht gestartet).[/dim]",
    "dashboard.inspect_col_tender": "Tender-ID",
    "dashboard.inspect_col_title": "Titel",
    "dashboard.inspect_col_step": "Schritt",
    "help.opt.inspect": "Einen Job anhand der vollstaendigen oder partiellen UUID inspizieren. Zeigt Live-Fortschrittsbalken, Enrichment-Schritte pro Tender (summary/searchable/saving/done) und das Worker-Log. Akzeptiert die ersten 8 Zeichen der Job-ID.",

    # ── Background Jobs ───────────────────────────────────────
    "bg.job_started": "[green]Job {job_id} im Hintergrund gestartet.[/green] Verwenden Sie [bold]tenderx dashboard[/bold] zur Ueberwachung.",
    "bg.job_type_enrichment": "KI-Anreicherung",
    "bg.job_type_docs_download": "Dokumenten-Download",
    "bg.job_type_embedding": "Embedding-Generierung",
    "bg.enrich_started_bg": "[green]Anreicherungsjob {job_id} im Hintergrund gestartet.[/green] Verwenden Sie [bold]tenderx dashboard[/bold] zur Ueberwachung.",
    "bg.kill_all_confirm": "[bold]{count}[/bold] aktive(n) Job(s) abbrechen?",
    "bg.kill_all_done": "[green]{count} Job(s) abgebrochen.[/green]",
    "bg.kill_all_none": "[dim]Keine aktiven Jobs zum Abbrechen.[/dim]",
    "bg.kill_one_done": "[green]Job {job_id} abgebrochen.[/green]",
    "bg.kill_one_not_found": "[red]Job {job_id} nicht gefunden.[/red]",
    "bg.kill_one_not_active": "[yellow]Job {job_id} ist nicht aktiv (Status: {status}).[/yellow]",
    "help.cmd.kill": "Hintergrundjobs abbrechen (einen per ID oder --all).",
    "help.opt.kill_all": "Alle aktiven Jobs abbrechen",

    # ── Common ─────────────────────────────────────────────────
    "common.db_unavailable": "[red]Datenbank nicht verfuegbar. Fuehren Sie zuerst 'docker compose up -d' aus.[/red]",
    "common.error": "[red]Fehler: {error}[/red]",

    # ── Language selection ─────────────────────────────────────
    "lang.menu_title": "Language / Idioma / Sprache",
    "lang.menu_prompt": "Select / Selecione / Wählen (1-4): ",
    "lang.menu_invalid": "[yellow]Bitte geben Sie 1, 2, 3 oder 4 ein.[/yellow]",
    "lang.changed": "\n[green]Sprache auf {lang_name} gesetzt.[/green]\n",
    "lang.current": "Aktuelle Sprache: [bold]{lang}[/bold] ({code})",
    "lang.reset_to_default": "[green]Sprache auf Englisch (en-US) zurueckgesetzt.[/green]",
}
