"""European Portuguese (pt-PT) translation strings.

Every other locale file must mirror exactly the same keys.
Rich markup ([green], [bold], etc.) is embedded in values.
Format placeholders use Python .format() syntax: {name}.
"""

STRINGS: dict[str, str] = {
    # ── Welcome Screen ─────────────────────────────────────────
    "welcome.tagline": "Plataforma de Inteligencia em Contratacao Publica Alema",
    "welcome.quick_start": "Inicio Rapido",
    "welcome.menu.ingest_run": "Ingerir concursos a partir da API de contratacao publica",
    "welcome.menu.ingest_enrich": "Executar enriquecimento com IA nos concursos armazenados",
    "welcome.menu.search_query": "Pesquisa semantica + estruturada de concursos",
    "welcome.menu.orgs_load": "Carregar organizacoes a partir de CSV",
    "welcome.menu.orgs_match": "Associar organizacoes a concursos relevantes",
    "welcome.menu.stats": "Mostrar estatisticas do sistema",
    "welcome.menu.docs_analyze": "Analisar portais de fornecedores de documentos",
    "welcome.menu.docs_download": "Descarregar documentos do portal de fornecedores",
    "welcome.menu.dashboard": "Monitorizar jobs em background em tempo real",
    "welcome.help_desc": "Mostrar todos os comandos e utilizacao detalhada",

    # ── Interactive Shell ──────────────────────────────────────
    "shell.hint": "Escreva 'help' para ver comandos, 'exit' para sair.",
    "shell.interrupted": "Interrompido.",
    "shell.goodbye": "Adeus!",
    "shell.invalid_input": "[red]Entrada invalida: {error}[/red]",

    # ── Help texts — app & groups ──────────────────────────────
    "help.app": "Plataforma de Inteligencia em Concursos Publicos Alemaes",
    "help.group.ingest": "Comandos de ingestao de concursos",
    "help.group.search": "Pesquisar e filtrar concursos",
    "help.group.orgs": "Gestao de organizacoes",
    "help.group.docs": "Comandos de armazenamento de documentos",
    "help.group.tender": "Comandos de inspecao de concursos",

    # ── Help texts — commands ──────────────────────────────────
    "help.cmd.ingest_run": "Ingerir concursos a partir da API de contratacao publica alema.",
    "help.cmd.ingest_enrich": "Executar enriquecimento com IA em concursos nao enriquecidos.",
    "help.cmd.dashboard": "Monitorizar jobs em background em tempo real.",
    "help.cmd.search_query": "Pesquisar concursos com filtros semanticos e estruturados.",
    "help.cmd.orgs_load": "Carregar organizacoes a partir de um ficheiro CSV.",
    "help.cmd.orgs_match": "Executar associacao de concursos para organizacoes.",
    "help.cmd.docs_analyze": "Analisar portais de fornecedores de documentos.",
    "help.cmd.docs_download": "Descarregar documentos de um portal de fornecedores.",
    "help.cmd.tender_show": "Mostrar informacao detalhada sobre um concurso.",
    "help.cmd.stats": "Mostrar estatisticas do sistema.",
    "help.cmd.purge": "Apagar TODOS os dados: registos da base de dados, objetos MinIO e ficheiros gerados.",
    "help.cmd.lang": "Alterar o idioma da CLI.",

    # ── Help texts — options ───────────────────────────────────
    "help.opt.days": "Numero de dias a ingerir",
    "help.opt.date": "Data especifica (AAAA-MM-DD)",
    "help.opt.enrich": "Executar enriquecimento com IA apos ingestao",
    "help.opt.query_text": "Consulta de pesquisa em texto livre",
    "help.opt.cpv": "Filtro por codigo CPV",
    "help.opt.nuts": "Filtro por codigo NUTS",
    "help.opt.min_value": "Valor estimado minimo",
    "help.opt.max_value": "Valor estimado maximo",
    "help.opt.limit": "Numero maximo de resultados",
    "help.opt.csv_path": "Caminho para o ficheiro CSV de organizacoes",
    "help.opt.org_id": "Associar uma organizacao especifica por UUID",
    "help.opt.all_orgs": "Associar todas as organizacoes",
    "help.opt.supplier": "Dominio do fornecedor para descarregar",
    "help.opt.tender_id": "UUID do concurso",
    "help.opt.verbose": "Mostrar descricoes detalhadas para cada metrica",
    "help.opt.yes": "Saltar pedido de confirmacao",
    "help.opt.lang_default": "Repor idioma para ingles (predefinicao)",
    "help.opt.bg": "Executar em background (sobrevive ao fecho da CLI, monitorize com 'tenderx dashboard')",
    "help.opt.enrich_bg": "Executar enriquecimento com IA em background apos ingestao",

    # ── Ingest ─────────────────────────────────────────────────
    "ingest.progress_date": "A ingerir concursos para {date}...",
    "ingest.progress_days": "A ingerir concursos dos ultimos {days} dias...",
    "ingest.done": (
        "\n[green]Concluido![/green] "
        "{fetched} obtidos, {inserted} novos, {updated} atualizados, "
        "{errors} erros ({duration}s)"
    ),
    "ingest.enrichment_running": "\nA executar enriquecimento com IA...",
    "ingest.enrichment_result": (
        "[green]Enriquecimento:[/green] "
        "{succeeded} enriquecidos, {failed} falhados, {skipped} ignorados"
    ),
    "ingest.ollama_unavailable": "[yellow]Ollama indisponivel \u2014 enriquecimento ignorado[/yellow]",
    "ingest.enrichment_skipped": "[yellow]Enriquecimento ignorado: {error}[/yellow]",
    "ingest.embeddings_running": "\nA gerar embeddings...",
    "ingest.embeddings_result": "[green]Embeddings:[/green] {count} gerados",
    "ingest.embeddings_skipped": "[yellow]Embeddings ignorados: {error}[/yellow]",

    # ── Ingest — enrich subcommand ─────────────────────────────
    "ingest.enrich_ollama_unavailable": "[red]Ollama indisponivel. Inicie-o primeiro.[/red]",
    "ingest.enrich_running": "A executar enriquecimento com IA...",
    "ingest.enrich_done": (
        "[green]Concluido![/green] "
        "{succeeded} enriquecidos, {failed} falhados, {skipped} ignorados ({duration}s)"
    ),

    # ── Search ─────────────────────────────────────────────────
    "search.no_results": "[yellow]Nenhum resultado encontrado.[/yellow]",
    "search.table_title": "Resultados da Pesquisa ({count})",
    "search.col_score": "Pontuacao",
    "search.col_title": "Titulo",
    "search.col_cpv": "CPV",
    "search.col_value": "Valor",
    "search.col_deadline": "Prazo",

    # ── Organizations ──────────────────────────────────────────
    "orgs.load_done": (
        "\n[green]Concluido![/green] "
        "{total} total, {inserted} novos, {updated} atualizados, {skipped} ignorados"
    ),
    "orgs.load_errors": "[yellow]Erros ({count}):[/yellow]",
    "orgs.file_not_found": "[red]Ficheiro nao encontrado: {path}[/red]",
    "orgs.match_specify": "[red]Especifique --org-id ou --all[/red]",
    "orgs.match_all_progress": "A associar todas as organizacoes...",
    "orgs.match_table_title": "Resultados da Associacao ({count})",
    "orgs.match_col_organization": "Organizacao",
    "orgs.match_col_queries": "Consultas",
    "orgs.match_col_matches": "Correspondencias",
    "orgs.match_col_source": "Origem",
    "orgs.match_one_progress": "A associar organizacao {uid}...",
    "orgs.match_one_org": "\nOrganizacao: [bold]{name}[/bold]",
    "orgs.match_one_source": "Origem da consulta: {source}",
    "orgs.match_one_queries": "\nConsultas:",
    "orgs.match_one_total": "\nTotal de correspondencias: {count}",
    "orgs.match_one_top": "\nMelhores correspondencias:",

    # ── Documents ──────────────────────────────────────────────
    "docs.no_portals": "[yellow]Nenhum URL de portal de documentos encontrado.[/yellow]",
    "docs.analyze_title": "Analise de Fornecedores de Documentos",
    "docs.col_domain": "Dominio",
    "docs.col_tenders": "Concursos",
    "docs.col_percent": "%",
    "docs.csv_saved": "\n[green]CSV guardado em {path}[/green]",
    "docs.download_done": (
        "\n[green]Concluido![/green] "
        "{tenders} concursos, {downloaded} descarregados, "
        "{failed} falhados, {bytes} bytes"
    ),

    # ── Tender show ────────────────────────────────────────────
    "tender.not_found": "[red]Concurso {id} nao encontrado.[/red]",
    "tender.label_contract": "Contrato:",
    "tender.label_type": "Tipo:",
    "tender.label_value": "Valor:",
    "tender.label_published": "Publicado:",
    "tender.label_deadline": "Prazo:",
    "tender.label_location": "Localizacao:",
    "tender.label_cpv": "CPV:",
    "tender.label_nuts": "NUTS:",
    "tender.label_platform": "Plataforma:",
    "tender.label_docs_portal": "Portal de Docs:",
    "tender.label_ai_summary": "Resumo IA:",
    "tender.label_issuer": "Entidade Adjudicante:",
    "tender.label_contact": "Contacto:",
    "tender.label_lots": "Lotes ({count}):",
    "tender.label_documents": "Documentos ({count}):",
    "tender.untitled": "Sem titulo",
    "tender.unknown_type": "desconhecido",

    # ── Stats ──────────────────────────────────────────────────
    "stats.table_title": "Estatisticas do Sistema",
    "stats.table_title_detailed": "Estatisticas do Sistema  [dim](detalhado)[/dim]",
    "stats.col_metric": "Metrica",
    "stats.col_value": "Valor",
    "stats.col_description": "Descricao",
    "stats.metric_tenders": "Total de Concursos",
    "stats.metric_issuers": "Total de Entidades Adjudicantes",
    "stats.metric_orgs": "Total de Organizacoes",
    "stats.metric_docs": "Total de Documentos",
    "stats.metric_matches": "Total de Correspondencias",
    "stats.metric_date_range": "Intervalo de Datas",
    "stats.metric_enriched": "Enriquecidos",
    "stats.metric_embedded": "Com Embedding",
    "stats.desc_tenders": (
        "Avisos de contratacao publica ingeridos de oeffentlichevergabe.de. "
        "Cada concurso representa uma oportunidade de contratacao publicada por uma entidade publica alema."
    ),
    "stats.desc_issuers": (
        "Entidades adjudicantes (Vergabestellen) distintas que publicaram concursos. "
        "Inclui organismos federais, estaduais e municipais de toda a Alemanha."
    ),
    "stats.desc_orgs": (
        "Entidades empresariais carregadas a partir do CSV do desafio. "
        "Sao potenciais concorrentes cujos perfis sao associados aos concursos disponiveis."
    ),
    "stats.desc_docs": (
        "Documentos de contratacao (PDFs, DOCX, etc.) descarregados de portais de fornecedores "
        "e armazenados no MinIO para acesso offline."
    ),
    "stats.desc_matches": (
        "Resultados de associacao organizacao-concurso produzidos pelo pipeline de associacao com IA. "
        "Cada correspondencia inclui uma pontuacao de semelhanca da pesquisa hibrida semantica + estruturada."
    ),
    "stats.desc_date_range": (
        "Intervalo de datas de publicacao dos concursos ingeridos. Reflete a janela temporal coberta "
        "pelos dados atualmente na base de dados."
    ),
    "stats.desc_enriched": (
        "Concursos processados pelo Ollama (gemma3:4b) para gerar um resumo com IA "
        "e texto pesquisavel. O enriquecimento melhora a relevancia da pesquisa e a legibilidade."
    ),
    "stats.desc_embedded": (
        "Concursos com embedding vetorial de 384 dimensoes (paraphrase-multilingual-MiniLM-L12-v2) "
        "armazenado no pgvector, permitindo pesquisa por semelhanca semantica."
    ),
    "stats.tip": (
        "\n[dim]Dica: execute [bold]tenderx stats --verbose[/bold] "
        "para descricoes detalhadas de cada metrica.[/dim]"
    ),

    # ── Purge ──────────────────────────────────────────────────
    "purge.header": "\n[bold red]PURGAR -- Os seguintes dados serao PERMANENTEMENTE apagados:[/bold red]\n",
    "purge.db_table_title": "Tabelas da Base de Dados",
    "purge.col_table": "Tabela",
    "purge.col_rows": "Registos",
    "purge.row_tenders": "tenders",
    "purge.row_with_summaries": "  - com resumos de IA",
    "purge.row_with_embeddings": "  - com embeddings (vetores de 384 dimensoes)",
    "purge.row_issuers": "issuers",
    "purge.row_organizations": "organizations",
    "purge.row_tender_lots": "tender_lots",
    "purge.row_tender_documents": "tender_documents",
    "purge.row_match_results": "match_results",
    "purge.total_rows": "[bold]Total de registos[/bold]",
    "purge.minio_bucket": "\n[bold]Bucket MinIO[/bold] ({bucket}): [yellow]{count} objetos[/yellow]",
    "purge.gen_files_header": "\n[bold]Ficheiros gerados[/bold] (data/output/):",
    "purge.gen_files_none": "\n[bold]Ficheiros gerados[/bold]: nenhum",
    "purge.nothing_to_purge": "\n[green]Nada a purgar -- o sistema ja esta limpo.[/green]",
    "purge.confirm": "Tem a certeza de que pretende apagar TUDO o que esta acima? Esta acao e irreversivel",
    "purge.aborted": "[yellow]Cancelado.[/yellow]",
    "purge.purging": "\n[bold]A purgar...[/bold]",
    "purge.truncating_db": "  A truncar tabelas da base de dados...",
    "purge.truncating_db_ok": "[green]OK[/green] {count} registos apagados",
    "purge.removing_minio": "  A remover objetos do MinIO...",
    "purge.removing_minio_ok": "[green]OK[/green] {count} objetos removidos",
    "purge.deleting_files": "  A apagar ficheiros gerados...",
    "purge.deleting_files_ok": "[green]OK[/green] {count} ficheiros apagados",
    "purge.complete": "\n[bold green]Purga concluida.[/bold green] O sistema esta limpo.\n",

    # ── Dashboard ──────────────────────────────────────────────
    "dashboard.title": "Dashboard de Jobs em Background",
    "dashboard.col_id": "ID",
    "dashboard.col_type": "Tipo",
    "dashboard.col_status": "Estado",
    "dashboard.col_progress": "Progresso",
    "dashboard.col_duration": "Duracao",
    "dashboard.col_errors": "Erros",
    "dashboard.no_jobs": "[dim]Nenhum job em background encontrado. Inicie um com a flag --bg.[/dim]",
    "dashboard.exit_hint": "[dim]Prima Ctrl+C para sair[/dim]",
    "dashboard.stale_detected": "[yellow]Detetado(s) {count} job(s) obsoleto(s) — marcado(s) como falhado(s).[/yellow]",

    # ── Background Jobs ───────────────────────────────────────
    "bg.job_started": "[green]Job {job_id} iniciado em background.[/green] Use [bold]tenderx dashboard[/bold] para monitorizar.",
    "bg.job_type_enrichment": "Enriquecimento IA",
    "bg.job_type_docs_download": "Download de Docs",
    "bg.enrich_started_bg": "[green]Job de enriquecimento {job_id} iniciado em background.[/green] Use [bold]tenderx dashboard[/bold] para monitorizar.",

    # ── Common ─────────────────────────────────────────────────
    "common.db_unavailable": "[red]Base de dados indisponivel. Execute 'docker compose up -d' primeiro.[/red]",
    "common.error": "[red]Erro: {error}[/red]",

    # ── Language selection ─────────────────────────────────────
    "lang.menu_title": "Language / Idioma / Sprache",
    "lang.menu_prompt": "Select / Selecione / Wählen (1-4): ",
    "lang.menu_invalid": "[yellow]Introduza 1, 2, 3 ou 4.[/yellow]",
    "lang.changed": "\n[green]Idioma definido para {lang_name}.[/green]\n",
    "lang.current": "Idioma atual: [bold]{lang}[/bold] ({code})",
    "lang.reset_to_default": "[green]Idioma reposto para ingles (en-US).[/green]",
}
