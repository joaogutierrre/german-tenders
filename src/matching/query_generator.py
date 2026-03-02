"""Generate search queries for organizations using LLM."""

import json
import logging

from src.ai.llm_client import LLMError, OllamaClient
from src.ai.prompts import GENERATE_QUERIES
from src.db.models import Organization

logger = logging.getLogger(__name__)


class QueryGenerator:
    """Generate procurement search queries for an organization."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    async def generate(self, org: Organization) -> tuple[list[str], str]:
        """Generate 5 search queries for an organization.

        Returns:
            Tuple of (queries, source) where source is 'llm' or 'fallback'.
        """
        try:
            if not await self.client.is_available():
                return self._fallback_queries(org), "fallback"

            prompt = GENERATE_QUERIES.format(
                name=org.name,
                website=org.website or "Unknown",
                description=org.description or f"Company: {org.name}",
            )

            response = await self.client.generate(prompt)
            queries = self._parse_json_queries(response)

            if queries and len(queries) >= 3:
                return queries[:5], "llm"

            logger.warning(
                "LLM returned invalid queries for %s, using fallback", org.name
            )
            return self._fallback_queries(org), "fallback"

        except LLMError as exc:
            logger.warning("LLM error for %s: %s, using fallback", org.name, exc)
            return self._fallback_queries(org), "fallback"

    def _parse_json_queries(self, text: str) -> list[str]:
        """Parse a JSON array of strings from LLM output."""
        text = text.strip()

        # Try to find JSON array in the text
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            return []

        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list) and all(isinstance(q, str) for q in parsed):
                return [q.strip() for q in parsed if q.strip()]
        except json.JSONDecodeError:
            pass

        return []

    def _fallback_queries(self, org: Organization) -> list[str]:
        """Generate basic queries from organization name and keywords."""
        name = org.name
        queries = [
            f"{name} public tender",
            f"{name} procurement services",
            f"{name} government contract",
            f"public tender {name.split()[0] if name.split() else name}",
            f"procurement {name} Germany",
        ]

        # Replace with keyword-based queries if available
        if org.industry_keywords:
            for i, kw in enumerate(org.industry_keywords[:3]):
                if i < len(queries):
                    queries[i] = f"{kw} public procurement Germany"

        return queries[:5]
