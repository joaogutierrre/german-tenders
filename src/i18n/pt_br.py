"""Brazilian Portuguese (pt-BR) translation strings.

Every other locale file must mirror exactly the same keys.
Rich markup ([green], [bold], etc.) is embedded in values.
Format placeholders use Python .format() syntax: {name}.
"""

STRINGS: dict[str, str] = {
    # ── Welcome Screen ─────────────────────────────────────────
    "welcome.tagline": "Plataforma de Inteligencia em Compras Publicas Alemas",
    "welcome.quick_start": "Inicio Rapido",
    "welcome.menu.ingest_run": "Ingerir licitacoes da API de compras publicas",
    "welcome.menu.ingest_enrich": "Executar enriquecimento com IA nas licitacoes armazenadas",
    "welcome.menu.ingest_embed": "Gerar embeddings vetoriais para busca",
    "welcome.menu.search_query": "Busca semantica + estruturada de licitacoes",
    "welcome.menu.orgs_load": "Carregar organizacoes a partir de CSV",
    "welcome.menu.orgs_match": "Combinar organizacoes com licitacoes relevantes",
    "welcome.menu.stats": "Exibir estatisticas do sistema",
    "welcome.menu.docs_analyze": "Analisar portais de fornecedores de documentos",
    "welcome.menu.docs_download": "Baixar documentos do portal de fornecedor",
    "welcome.menu.dashboard": "Monitorar jobs em background em tempo real",
    "welcome.menu.tender_list": "Listar e inspecionar licitacoes armazenadas",
    "welcome.menu.kill": "Cancelar jobs em background",
    "welcome.menu.lang": "Alterar o idioma da CLI",
    "welcome.menu.purge": "Excluir TODOS os dados (BD + MinIO + arquivos)",
    "welcome.help_desc": "Exibir todos os comandos e uso detalhado",

    # ── Detailed help (tenderx help) ────────────────────────────
    "help.detailed.title": "TenderX — Referencia de Comandos",
    "help.detailed.section_ingest": "Ingestao",
    "help.detailed.section_search": "Busca",
    "help.detailed.section_orgs": "Organizacoes",
    "help.detailed.section_docs": "Documentos",
    "help.detailed.section_tender": "Licitacoes",
    "help.detailed.section_system": "Sistema",
    "help.detailed.footer": "[dim]Dica: execute qualquer comando com --help para detalhes completos (ex: tenderx ingest run --help)[/dim]",

    # ── Interactive Shell ──────────────────────────────────────
    "shell.hint": "Digite 'help' para ver os comandos, 'exit' para sair.",
    "shell.interrupted": "Interrompido.",
    "shell.goodbye": "Ate mais!",
    "shell.invalid_input": "[red]Entrada invalida: {error}[/red]",

    # ── Help texts — app & groups ──────────────────────────────
    "help.app": "Plataforma de Inteligencia em Licitacoes Alemas",
    "help.group.ingest": "Comandos de ingestao de licitacoes",
    "help.group.search": "Busca e filtragem de licitacoes",
    "help.group.orgs": "Gerenciamento de organizacoes",
    "help.group.docs": "Comandos de armazenamento de documentos",
    "help.group.tender": "Comandos de inspecao de licitacoes",

    # ── Help texts — commands ──────────────────────────────────
    "help.cmd.ingest_run": "Ingerir licitacoes da API de compras publicas alema.",
    "help.cmd.ingest_enrich": "Executar enriquecimento com IA em licitacoes nao enriquecidas.",
    "help.cmd.ingest_embed": "Gerar embeddings vetoriais para licitacoes enriquecidas.",
    "help.cmd.dashboard": "Monitorar jobs em background em tempo real. Exibe uma tabela live com barras de progresso de todos os jobs. Use --inspect <job-id> para detalhar um job específico.",
    "help.cmd.search_query": "Buscar licitacoes com filtros semanticos e estruturados.",
    "help.cmd.orgs_load": "Carregar organizacoes a partir de um arquivo CSV.",
    "help.cmd.orgs_match": "Executar correspondencia de licitacoes para organizacoes.",
    "help.cmd.docs_analyze": "Analisar portais de fornecedores de documentos.",
    "help.cmd.docs_download": "Baixar documentos de um portal de fornecedor.",
    "help.cmd.tender_list": "Listar licitacoes com filtros opcionais.",
    "help.cmd.tender_show": "Exibir informacoes detalhadas sobre uma licitacao.",
    "help.cmd.stats": "Exibir estatisticas do sistema.",
    "help.cmd.purge": "Excluir TODOS os dados: registros do banco, objetos do MinIO e arquivos gerados.",
    "help.cmd.lang": "Alterar o idioma da CLI.",

    # ── Help texts — options ───────────────────────────────────
    "help.opt.days": "Numero de dias para ingestao",
    "help.opt.date": "Data especifica (AAAA-MM-DD)",
    "help.opt.enrich": "Executar enriquecimento com IA apos ingestao",
    "help.opt.query_text": "Consulta de busca em texto livre",
    "help.opt.cpv": "Filtro por codigo CPV",
    "help.opt.nuts": "Filtro por codigo NUTS",
    "help.opt.min_value": "Valor estimado minimo",
    "help.opt.max_value": "Valor estimado maximo",
    "help.opt.limit": "Maximo de resultados",
    "help.opt.csv_path": "Caminho para o CSV de organizacoes",
    "help.opt.org_id": "UUID de uma organizacao especifica para correspondencia",
    "help.opt.all_orgs": "Fazer correspondencia de todas as organizacoes",
    "help.opt.supplier": "Dominio do fornecedor para download",
    "help.opt.tender_id": "UUID da licitacao",
    "help.opt.verbose": "Exibir descricoes detalhadas para cada metrica",
    "help.opt.yes": "Pular confirmacao",
    "help.opt.enriched_only": "Exibir apenas licitacoes enriquecidas (com resumo IA)",
    "help.opt.lang_default": "Redefinir idioma para ingles (padrao)",
    "help.opt.bg": "Executar em background (sobrevive ao fechamento da CLI, monitore com 'tenderx dashboard')",
    "help.opt.enrich_bg": "Executar enriquecimento com IA em background apos ingestao",
    "help.opt.gpu": "Ativar enriquecimento paralelo com GPU (10 simultaneos, requer GPU NVIDIA)",
    "help.opt.archive": "Arquivar exports brutos da API no MinIO (padrao: ativado)",

    # ── Ingest ─────────────────────────────────────────────────
    "ingest.progress_date": "Ingerindo licitacoes para {date}...",
    "ingest.progress_days": "Ingerindo licitacoes dos ultimos {days} dias...",
    "ingest.done": (
        "\n[green]Concluido![/green] "
        "{fetched} obtidas, {inserted} novas, {updated} atualizadas, "
        "{errors} erros ({duration}s)"
    ),
    "ingest.enrichment_running": "\nExecutando enriquecimento com IA...",
    "ingest.enrichment_result": (
        "[green]Enriquecimento:[/green] "
        "{succeeded} enriquecidas, {failed} com falha, {skipped} ignoradas"
    ),
    "ingest.ollama_unavailable": "[yellow]Ollama nao disponivel \u2014 enriquecimento ignorado[/yellow]",
    "ingest.enrichment_skipped": "[yellow]Enriquecimento ignorado: {error}[/yellow]",
    "ingest.ocds_enriching": "Enriquecendo URLs de documentos via OCDS...",
    "ingest.ocds_result": "[green]OCDS:[/green] {updated} URLs enriquecidas, {not_found} nao encontradas",
    "ingest.ocds_skipped": "[dim]Enriquecimento OCDS: dados indisponiveis[/dim]",
    "ingest.archived_export": "[dim]Arquivado {fmt} para {date}[/dim]",
    "ingest.archive_skipped": "[dim]Arquivamento de exports desativado[/dim]",
    "ingest.embeddings_running": "\nGerando embeddings...",
    "ingest.embeddings_result": "[green]Embeddings:[/green] {count} gerados",
    "ingest.embeddings_skipped": "[yellow]Embeddings ignorados: {error}[/yellow]",

    # ── Ingest — enrich subcommand ─────────────────────────────
    "ingest.enrich_ollama_unavailable": "[red]Ollama nao disponivel. Inicie-o primeiro.[/red]",
    "ingest.enrich_running": "Executando enriquecimento com IA...",
    "ingest.enrich_done": (
        "[green]Concluido![/green] "
        "{succeeded} enriquecidas, {failed} com falha, {skipped} ignoradas ({duration}s)"
    ),

    # ── Search ─────────────────────────────────────────────────
    "search.no_results": "[yellow]Nenhum resultado encontrado.[/yellow]",
    "search.table_title": "Resultados da Busca ({count})",
    "search.col_id": "ID",
    "search.col_score": "Pontuacao",
    "search.col_title": "Titulo",
    "search.col_cpv": "CPV",
    "search.col_value": "Valor",
    "search.col_deadline": "Prazo",

    # ── Organizations ──────────────────────────────────────────
    "orgs.load_done": (
        "\n[green]Concluido![/green] "
        "{total} total, {inserted} novas, {updated} atualizadas, {skipped} ignoradas"
    ),
    "orgs.load_errors": "[yellow]Erros ({count}):[/yellow]",
    "orgs.file_not_found": "[red]Arquivo nao encontrado: {path}[/red]",
    "orgs.match_specify": "[red]Especifique --org-id ou --all[/red]",
    "orgs.match_all_progress": "Fazendo correspondencia de todas as organizacoes...",
    "orgs.match_table_title": "Resultados da Correspondencia ({count})",
    "orgs.match_col_organization": "Organizacao",
    "orgs.match_col_queries": "Consultas",
    "orgs.match_col_matches": "Correspondencias",
    "orgs.match_col_source": "Origem",
    "orgs.match_one_progress": "Fazendo correspondencia da organizacao {uid}...",
    "orgs.match_one_org": "\nOrganizacao: [bold]{name}[/bold]",
    "orgs.match_one_source": "Origem da consulta: {source}",
    "orgs.match_one_queries": "\nConsultas:",
    "orgs.match_one_total": "\nTotal de correspondencias: {count}",
    "orgs.match_one_top": "\nMelhores correspondencias:",

    # ── Documents ──────────────────────────────────────────────
    "docs.no_portals": "[yellow]Nenhuma URL de portal de documentos encontrada.[/yellow]",
    "docs.analyze_title": "Analise de Fornecedores de Documentos",
    "docs.col_domain": "Dominio",
    "docs.col_tenders": "Licitacoes",
    "docs.col_percent": "%",
    "docs.csv_saved": "\n[green]CSV salvo em {path}[/green]",
    "docs.download_done": (
        "\n[green]Concluido![/green] "
        "{tenders} licitacoes, {downloaded} baixados, "
        "{failed} com falha, {no_links} sem links, {bytes} bytes"
    ),

    # ── Tender show ────────────────────────────────────────────
    "tender.not_found": "[red]Licitacao {id} nao encontrada.[/red]",
    "tender.label_contract": "Contrato:",
    "tender.label_type": "Tipo:",
    "tender.label_value": "Valor:",
    "tender.label_published": "Publicado:",
    "tender.label_deadline": "Prazo:",
    "tender.label_location": "Local:",
    "tender.label_cpv": "CPV:",
    "tender.label_nuts": "NUTS:",
    "tender.label_platform": "Plataforma:",
    "tender.label_docs_portal": "Portal de Docs:",
    "tender.label_ai_summary": "Resumo IA:",
    "tender.label_embedding": "Embedding:",
    "tender.label_issuer": "Emissor:",
    "tender.label_contact": "Contato:",
    "tender.label_lots": "Lotes ({count}):",
    "tender.label_documents": "Documentos ({count}):",
    "tender.list_title": "Licitacoes ({count})",
    "tender.untitled": "Sem titulo",
    "tender.unknown_type": "desconhecido",

    # ── Stats ──────────────────────────────────────────────────
    "stats.table_title": "Estatisticas do Sistema",
    "stats.table_title_detailed": "Estatisticas do Sistema  [dim](detalhado)[/dim]",
    "stats.col_metric": "Metrica",
    "stats.col_value": "Valor",
    "stats.col_description": "Descricao",
    "stats.metric_tenders": "Total de Licitacoes",
    "stats.metric_issuers": "Total de Emissores",
    "stats.metric_orgs": "Total de Organizacoes",
    "stats.metric_docs": "Total de Documentos",
    "stats.metric_matches": "Total de Correspondencias",
    "stats.metric_date_range": "Periodo",
    "stats.metric_enriched": "Enriquecidas",
    "stats.metric_embedded": "Com Embedding",
    "stats.desc_tenders": (
        "Avisos de compras publicas ingeridos do oeffentlichevergabe.de. "
        "Cada licitacao representa uma oportunidade de contratacao publicada por uma autoridade publica alema."
    ),
    "stats.desc_issuers": (
        "Autoridades contratantes distintas (Vergabestellen) que publicaram licitacoes. "
        "Inclui orgaos federais, estaduais e municipais de toda a Alemanha."
    ),
    "stats.desc_orgs": (
        "Entidades empresariais carregadas a partir do CSV do desafio. "
        "Sao potenciais licitantes cujos perfis sao comparados com as licitacoes disponiveis."
    ),
    "stats.desc_docs": (
        "Documentos de licitacao (PDFs, DOCX, etc.) baixados de portais de fornecedores "
        "e armazenados no MinIO para acesso offline."
    ),
    "stats.desc_matches": (
        "Resultados de correspondencia entre organizacoes e licitacoes produzidos pelo pipeline de IA. "
        "Cada correspondencia inclui uma pontuacao de similaridade da busca hibrida semantica + estruturada."
    ),
    "stats.desc_date_range": (
        "Intervalo de datas de publicacao das licitacoes ingeridas. Reflete a janela de tempo coberta "
        "pelos dados atualmente no banco de dados."
    ),
    "stats.desc_enriched": (
        "Licitacoes processadas pelo Ollama (gemma3:4b) para gerar um resumo com IA "
        "e texto pesquisavel. O enriquecimento melhora a relevancia da busca e a legibilidade."
    ),
    "stats.desc_embedded": (
        "Licitacoes com embedding vetorial de 384 dimensoes (paraphrase-multilingual-MiniLM-L12-v2) "
        "armazenado no pgvector, permitindo busca por similaridade semantica."
    ),
    "stats.tip": (
        "\n[dim]Dica: execute [bold]tenderx stats --verbose[/bold] "
        "para ver descricoes detalhadas de cada metrica.[/dim]"
    ),

    # ── Purge ──────────────────────────────────────────────────
    "purge.header": "\n[bold red]PURGE -- Os seguintes dados serao PERMANENTEMENTE excluidos:[/bold red]\n",
    "purge.db_table_title": "Tabelas do Banco de Dados",
    "purge.col_table": "Tabela",
    "purge.col_rows": "Registros",
    "purge.row_tenders": "tenders",
    "purge.row_with_summaries": "  - com resumos de IA",
    "purge.row_with_embeddings": "  - com embeddings (vetores de 384 dimensoes)",
    "purge.row_issuers": "issuers",
    "purge.row_organizations": "organizations",
    "purge.row_tender_lots": "tender_lots",
    "purge.row_tender_documents": "tender_documents",
    "purge.row_match_results": "match_results",
    "purge.total_rows": "[bold]Total de registros[/bold]",
    "purge.minio_bucket": "\n[bold]Bucket MinIO[/bold] ({bucket}): [yellow]{count} objetos[/yellow]",
    "purge.gen_files_header": "\n[bold]Arquivos gerados[/bold] (data/output/):",
    "purge.gen_files_none": "\n[bold]Arquivos gerados[/bold]: nenhum",
    "purge.nothing_to_purge": "\n[green]Nada para limpar -- o sistema ja esta limpo.[/green]",
    "purge.confirm": "Tem certeza que deseja excluir TUDO acima? Esta acao nao pode ser desfeita",
    "purge.aborted": "[yellow]Cancelado.[/yellow]",
    "purge.purging": "\n[bold]Limpando...[/bold]",
    "purge.truncating_db": "  Truncando tabelas do banco de dados...",
    "purge.truncating_db_ok": "[green]OK[/green] {count} registros excluidos",
    "purge.removing_minio": "  Removendo objetos do MinIO...",
    "purge.removing_minio_ok": "[green]OK[/green] {count} objetos removidos",
    "purge.deleting_files": "  Excluindo arquivos gerados...",
    "purge.deleting_files_ok": "[green]OK[/green] {count} arquivos excluidos",
    "purge.complete": "\n[bold green]Limpeza concluida.[/bold green] O sistema esta limpo.\n",

    # ── Dashboard ──────────────────────────────────────────────
    "dashboard.title": "Dashboard de Jobs em Background",
    "dashboard.col_id": "ID",
    "dashboard.col_type": "Tipo",
    "dashboard.col_status": "Status",
    "dashboard.col_progress": "Progresso",
    "dashboard.col_duration": "Duracao",
    "dashboard.col_errors": "Erros",
    "dashboard.no_jobs": "[dim]Nenhum job em background encontrado. Inicie um com a flag --bg.[/dim]",
    "dashboard.exit_hint": "[dim]Pressione Ctrl+C para sair[/dim]",
    "dashboard.stale_detected": "[yellow]Detectado(s) {count} job(s) obsoleto(s) — marcado(s) como falho(s).[/yellow]",
    "dashboard.inspect_title": "Inspecionar Job {job_id}",
    "dashboard.inspect_not_found": "[red]Job {job_id} nao encontrado.[/red]",
    "dashboard.inspect_status": "Status: {status}  |  Progresso: {progress}  |  Duracao: {duration}",
    "dashboard.inspect_log_title": "Log do Worker (ultimas {lines} linhas)",
    "dashboard.inspect_tenders_title": "Progresso por Tender",
    "dashboard.inspect_no_state": "[dim]Estado por tender nao disponivel (modo sequencial ou job nao iniciado).[/dim]",
    "dashboard.inspect_col_tender": "Tender ID",
    "dashboard.inspect_col_title": "Titulo",
    "dashboard.inspect_col_step": "Etapa",
    "help.opt.inspect": "Detalhar um job pelo UUID completo ou parcial. Mostra barra de progresso live, etapas de enrichment por tender (summary/searchable/saving/done) e tail do log do worker. Aceita os primeiros 8 caracteres do ID.",

    # ── Background Jobs ───────────────────────────────────────
    "bg.job_started": "[green]Job {job_id} iniciado em background.[/green] Use [bold]tenderx dashboard[/bold] para monitorar.",
    "bg.job_type_enrichment": "Enriquecimento IA",
    "bg.job_type_docs_download": "Download de Docs",
    "bg.job_type_embedding": "Geracao de Embeddings",
    "bg.enrich_started_bg": "[green]Job de enriquecimento {job_id} iniciado em background.[/green] Use [bold]tenderx dashboard[/bold] para monitorar.",
    "bg.kill_all_confirm": "Cancelar [bold]{count}[/bold] job(s) ativo(s)?",
    "bg.kill_all_done": "[green]{count} job(s) cancelado(s).[/green]",
    "bg.kill_all_none": "[dim]Nenhum job ativo para cancelar.[/dim]",
    "bg.kill_one_done": "[green]Job {job_id} cancelado.[/green]",
    "bg.kill_one_not_found": "[red]Job {job_id} não encontrado.[/red]",
    "bg.kill_one_not_active": "[yellow]Job {job_id} não está ativo (status: {status}).[/yellow]",
    "help.cmd.kill": "Cancelar jobs em background (um por ID, ou --all).",
    "help.opt.kill_all": "Cancelar todos os jobs ativos",

    # ── Common ─────────────────────────────────────────────────
    "common.db_unavailable": "[red]Banco de dados nao disponivel. Execute 'docker compose up -d' primeiro.[/red]",
    "common.error": "[red]Erro: {error}[/red]",

    # ── Language selection ─────────────────────────────────────
    "lang.menu_title": "Language / Idioma / Sprache",
    "lang.menu_prompt": "Select / Selecione / Wählen (1-4): ",
    "lang.menu_invalid": "[yellow]Por favor, digite 1, 2, 3 ou 4.[/yellow]",
    "lang.changed": "\n[green]Idioma definido para {lang_name}.[/green]\n",
    "lang.current": "Idioma atual: [bold]{lang}[/bold] ({code})",
    "lang.reset_to_default": "[green]Idioma redefinido para ingles (en-US).[/green]",
}
