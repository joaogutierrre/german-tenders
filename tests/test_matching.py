"""Tests for matching (Phase 6)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.ai.llm_client import LLMError, OllamaClient
from src.matching.query_generator import QueryGenerator


class TestQueryGenerator:
    def _make_org(
        self,
        name: str = "Test GmbH",
        website: str | None = "https://test.de",
        description: str | None = None,
        keywords: list[str] | None = None,
    ) -> MagicMock:
        """Create a mock Organization."""
        org = MagicMock()
        org.name = name
        org.website = website
        org.description = description
        org.industry_keywords = keywords
        return org

    @pytest.mark.asyncio
    async def test_generates_5_queries_from_llm(self) -> None:
        client = AsyncMock(spec=OllamaClient)
        client.is_available.return_value = True
        client.generate.return_value = json.dumps([
            "IT consulting Germany",
            "software development public sector",
            "cloud services federal agency",
            "data analytics government",
            "digital transformation Bavaria",
        ])

        gen = QueryGenerator(client=client)
        org = self._make_org()

        queries, source = await gen.generate(org)

        assert len(queries) == 5
        assert source == "llm"
        assert all(isinstance(q, str) for q in queries)

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self) -> None:
        client = AsyncMock(spec=OllamaClient)
        client.is_available.return_value = True
        client.generate.return_value = "This is not JSON at all"

        gen = QueryGenerator(client=client)
        org = self._make_org(name="Acme Corp")

        queries, source = await gen.generate(org)

        assert source == "fallback"
        assert len(queries) == 5
        assert any("Acme" in q for q in queries)

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self) -> None:
        client = AsyncMock(spec=OllamaClient)
        client.is_available.return_value = True
        client.generate.side_effect = LLMError("timeout")

        gen = QueryGenerator(client=client)
        org = self._make_org(name="Acme Corp")

        queries, source = await gen.generate(org)

        assert source == "fallback"
        assert len(queries) == 5

    @pytest.mark.asyncio
    async def test_fallback_when_ollama_unavailable(self) -> None:
        client = AsyncMock(spec=OllamaClient)
        client.is_available.return_value = False

        gen = QueryGenerator(client=client)
        org = self._make_org(name="Munich IT")

        queries, source = await gen.generate(org)

        assert source == "fallback"
        assert len(queries) == 5

    @pytest.mark.asyncio
    async def test_fallback_queries_contain_org_name(self) -> None:
        client = AsyncMock(spec=OllamaClient)
        client.is_available.return_value = False

        gen = QueryGenerator(client=client)
        org = self._make_org(name="Berlin Solutions AG")

        queries, _ = await gen.generate(org)

        assert any("Berlin" in q for q in queries)

    def test_parse_json_queries_with_surrounding_text(self) -> None:
        gen = QueryGenerator(client=AsyncMock())
        text = 'Here are the queries: ["query1", "query2", "query3", "query4", "query5"] hope this helps!'
        result = gen._parse_json_queries(text)
        assert len(result) == 5
        assert result[0] == "query1"

    def test_parse_json_queries_empty_on_invalid(self) -> None:
        gen = QueryGenerator(client=AsyncMock())
        assert gen._parse_json_queries("not json") == []
        assert gen._parse_json_queries("") == []

    @pytest.mark.asyncio
    async def test_llm_returns_too_few_queries_uses_fallback(self) -> None:
        client = AsyncMock(spec=OllamaClient)
        client.is_available.return_value = True
        client.generate.return_value = json.dumps(["only one"])

        gen = QueryGenerator(client=client)
        org = self._make_org()

        queries, source = await gen.generate(org)

        assert source == "fallback"
        assert len(queries) == 5
