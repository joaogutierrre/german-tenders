"""Tender matching pipeline — match organizations to relevant tenders."""

import logging
from dataclasses import dataclass, field
from uuid import UUID

from src.ai.llm_client import OllamaClient
from src.db.repositories import MatchResultRepository, OrganizationRepository
from src.db.session import get_session
from src.matching.query_generator import QueryGenerator
from src.search.hybrid import SearchResult, search_hybrid
from src.search.structured import SearchFilters

logger = logging.getLogger(__name__)


@dataclass
class MatchingResult:
    """Result of matching a single organization."""

    organization_name: str = ""
    queries: list[str] = field(default_factory=list)
    query_source: str = "unknown"
    total_matches: int = 0
    top_matches: list[tuple[str, float]] = field(default_factory=list)


class TenderMatcher:
    """Match organizations to relevant tenders."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self.generator = QueryGenerator(client or OllamaClient())

    async def match_organization(self, org_id: UUID) -> MatchingResult:
        """Match a single organization to tenders.

        Generates queries, runs hybrid search, deduplicates, and saves results.
        """
        result = MatchingResult()

        async with get_session() as session:
            org_repo = OrganizationRepository(session)
            match_repo = MatchResultRepository(session)

            org = await org_repo.find_by_id(org_id)
            if not org:
                logger.error("Organization %s not found", org_id)
                return result

            result.organization_name = org.name

            # Generate queries
            queries, source = await self.generator.generate(org)
            result.queries = queries
            result.query_source = source

            # Run search for each query and deduplicate
            seen: dict[UUID, tuple[str, float, str]] = {}  # tender_id -> (title, score, query)

            for query in queries:
                try:
                    search_results = await search_hybrid(
                        session,
                        query=query,
                        filters=SearchFilters(),
                        limit=10,
                    )
                    for sr in search_results:
                        tid = sr.tender.id
                        score = sr.semantic_score or 0.0
                        if tid not in seen or score > seen[tid][1]:
                            seen[tid] = (sr.tender.title, score, query)
                except Exception as exc:
                    logger.warning("Search error for query '%s': %s", query, exc)

            # Replace previous results for this org
            await match_repo.delete_by_org(org_id)

            # Save deduplicated results
            for tid, (title, score, query) in seen.items():
                await match_repo.save(
                    org_id=org_id,
                    tender_id=tid,
                    query_text=query,
                    score=score,
                )

            await session.commit()

            result.total_matches = len(seen)
            # Sort by score descending
            sorted_matches = sorted(seen.values(), key=lambda x: x[1], reverse=True)
            result.top_matches = [(title, score) for title, score, _ in sorted_matches]

        return result

    async def match_all(self) -> list[MatchingResult]:
        """Match all organizations to tenders."""
        results: list[MatchingResult] = []

        async with get_session() as session:
            org_repo = OrganizationRepository(session)
            orgs = await org_repo.find_all()

        if not orgs:
            logger.info("No organizations to match")
            return results

        logger.info("Matching %d organizations", len(orgs))

        for org in orgs:
            try:
                result = await self.match_organization(org.id)
                results.append(result)
                logger.info(
                    "Matched %s: %d results (%s)",
                    org.name,
                    result.total_matches,
                    result.query_source,
                )
            except Exception as exc:
                logger.error("Error matching %s: %s", org.name, exc)
                results.append(
                    MatchingResult(
                        organization_name=org.name,
                        total_matches=0,
                    )
                )

        return results
