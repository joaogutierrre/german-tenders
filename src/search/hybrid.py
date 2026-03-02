"""Hybrid search — combine semantic similarity with structured filters."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Tender
from src.db.repositories import TenderRepository
from src.search.embeddings import encode_text
from src.search.structured import SearchFilters, build_filter_query


@dataclass
class SearchResult:
    """A search result with optional scores."""

    tender: Tender
    semantic_score: float | None = None


async def search_hybrid(
    session: AsyncSession,
    query: str | None = None,
    filters: SearchFilters | None = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Execute a hybrid search combining semantic and structured filters.

    If query is provided and embeddings exist, results are ranked by cosine
    similarity. Structured filters are applied as WHERE clauses.

    Args:
        session: Database session.
        query: Free-text search query (optional).
        filters: Structured filters (optional).
        limit: Maximum results.

    Returns:
        List of SearchResult sorted by relevance.
    """
    if not filters:
        filters = SearchFilters()

    # Semantic-only search
    if query and not filters.has_filters:
        return await _semantic_search(session, query, limit)

    # Structured-only search
    if not query:
        return await _structured_search(session, filters, limit)

    # Hybrid: structured filters + semantic ranking
    return await _hybrid_search(session, query, filters, limit)


async def _semantic_search(
    session: AsyncSession, query: str, limit: int
) -> list[SearchResult]:
    """Pure semantic search via TenderRepository (pgvector)."""
    query_embedding = encode_text(query)
    repo = TenderRepository(session)

    rows = await repo.search_by_vector(query_embedding, limit=limit)

    results = []
    for tender_id, similarity in rows:
        tender = await session.get(Tender, tender_id)
        if tender:
            results.append(SearchResult(tender=tender, semantic_score=similarity))
    return results


async def _structured_search(
    session: AsyncSession, filters: SearchFilters, limit: int
) -> list[SearchResult]:
    """Pure structured search."""
    stmt = build_filter_query(filters).limit(limit)
    result = await session.execute(stmt)
    tenders = result.scalars().all()
    return [SearchResult(tender=t) for t in tenders]


async def _hybrid_search(
    session: AsyncSession, query: str, filters: SearchFilters, limit: int
) -> list[SearchResult]:
    """Combined structured + semantic search.

    Strategy: apply structured filters first, then re-rank by semantic similarity.
    """
    # Get candidates from structured search (wider window)
    candidate_limit = min(limit * 5, 200)
    stmt = build_filter_query(filters).where(
        Tender.embedding.isnot(None)
    ).limit(candidate_limit)
    result = await session.execute(stmt)
    candidates = list(result.scalars().all())

    if not candidates:
        # Fallback: structured without embedding requirement
        stmt = build_filter_query(filters).limit(limit)
        result = await session.execute(stmt)
        tenders = result.scalars().all()
        return [SearchResult(tender=t) for t in tenders]

    # Score candidates by semantic similarity
    query_embedding = encode_text(query)

    scored: list[SearchResult] = []
    for tender in candidates:
        if tender.embedding is not None:
            # Compute cosine similarity in Python
            sim = _cosine_similarity(query_embedding, list(tender.embedding))
            scored.append(SearchResult(tender=tender, semantic_score=sim))
        else:
            scored.append(SearchResult(tender=tender, semantic_score=0.0))

    scored.sort(key=lambda r: r.semantic_score or 0.0, reverse=True)
    return scored[:limit]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
