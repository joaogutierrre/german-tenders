"""Semantic (vector similarity) search using pgvector.

Note: This module provides a standalone semantic search function.
For production use, prefer ``search_hybrid()`` from ``src.search.hybrid``
which delegates vector queries to ``TenderRepository.search_by_vector()``.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Tender
from src.db.repositories import TenderRepository
from src.search.embeddings import encode_text


@dataclass
class SemanticResult:
    """A tender with its similarity score."""

    tender: Tender
    score: float


async def search_semantic(
    session: AsyncSession,
    query: str,
    limit: int = 20,
) -> list[SemanticResult]:
    """Search tenders by semantic similarity using pgvector cosine distance.

    Args:
        session: Database session.
        query: Free-text search query.
        limit: Maximum results to return.

    Returns:
        List of (tender, score) sorted by descending similarity.
    """
    query_embedding = encode_text(query)
    repo = TenderRepository(session)

    rows = await repo.search_by_vector(query_embedding, limit=limit)

    results = []
    for tender_id, similarity in rows:
        tender = await session.get(Tender, tender_id)
        if tender:
            results.append(SemanticResult(tender=tender, score=similarity))

    return results
