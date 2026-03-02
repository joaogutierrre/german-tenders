"""Tests for AI enrichment (Phase 3)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.llm_client import LLMError, OllamaClient
from src.ai.prompts import GENERATE_QUERIES, TENDER_SEARCHABLE, TENDER_SUMMARY
from src.ingestion.enrichment import (
    MAX_SEARCHABLE_LEN,
    MAX_SUMMARY_LEN,
    EnrichmentPipeline,
    EnrichmentResult,
)


# ── Prompt formatting ──────────────────────────────────────────

class TestPrompts:
    def test_summary_prompt_formats(self) -> None:
        result = TENDER_SUMMARY.format(
            title="Road construction",
            description="Building a highway",
            cpv_codes="45000000",
            issuer_name="Berlin City",
            deadline="2026-06-01",
        )
        assert "Road construction" in result
        assert "Berlin City" in result
        assert "45000000" in result

    def test_searchable_prompt_formats(self) -> None:
        result = TENDER_SEARCHABLE.format(
            title="IT services",
            description="Cloud migration",
            cpv_codes="72000000",
            contract_type="services",
            location="Munich",
            nuts_codes="DE212",
        )
        assert "IT services" in result
        assert "Cloud migration" in result
        assert "DE212" in result

    def test_generate_queries_prompt_formats(self) -> None:
        result = GENERATE_QUERIES.format(
            name="Acme GmbH",
            website="https://acme.de",
            description="Software development company",
        )
        assert "Acme GmbH" in result
        assert "acme.de" in result


# ── OllamaClient ───────────────────────────────────────────────

class TestOllamaClient:
    @pytest.mark.asyncio
    async def test_generate_calls_correct_url(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "test output"}
        mock_response.raise_for_status = MagicMock()

        with patch("src.ai.llm_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            client = OllamaClient(base_url="http://test:11434", model="testmodel")
            result = await client.generate("hello")

            assert result == "test output"
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://test:11434/api/generate"
            payload = call_args[1]["json"]
            assert payload["model"] == "testmodel"
            assert payload["prompt"] == "hello"
            assert payload["stream"] is False

    @pytest.mark.asyncio
    async def test_generate_with_system(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "ok"}
        mock_response.raise_for_status = MagicMock()

        with patch("src.ai.llm_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            client = OllamaClient(base_url="http://test:11434")
            await client.generate("prompt", system="sys")

            payload = mock_client.post.call_args[1]["json"]
            assert payload["system"] == "sys"

    @pytest.mark.asyncio
    async def test_generate_raises_on_timeout(self) -> None:
        import httpx

        with patch("src.ai.llm_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            client = OllamaClient(base_url="http://test:11434")
            with pytest.raises(LLMError, match="timeout"):
                await client.generate("hello")

    @pytest.mark.asyncio
    async def test_is_available_true(self) -> None:
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("src.ai.llm_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            client = OllamaClient(base_url="http://test:11434")
            assert await client.is_available() is True

    @pytest.mark.asyncio
    async def test_is_available_false_on_connection_error(self) -> None:
        import httpx

        with patch("src.ai.llm_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            client = OllamaClient(base_url="http://test:11434")
            assert await client.is_available() is False


# ── EnrichmentPipeline ─────────────────────────────────────────

class TestEnrichmentPipeline:
    def _make_mock_tender(self, tid: str = "00000000-0000-0000-0000-000000000001"):
        """Create a mock tender object."""
        from unittest.mock import MagicMock
        from uuid import UUID

        t = MagicMock()
        t.id = UUID(tid)
        t.title = "Test Tender"
        t.cpv_codes = ["72000000"]
        t.nuts_codes = ["DE212"]
        t.contract_type = "services"
        t.execution_location = "Berlin"
        t.submission_deadline = None
        t.raw_data = {"description": "A tender for IT services"}
        return t

    @pytest.mark.asyncio
    async def test_run_produces_summary_and_searchable(self) -> None:
        client = AsyncMock(spec=OllamaClient)
        client.is_available.return_value = True
        client.generate.side_effect = [
            "Short summary of tender",
            "Rich searchable text with keywords",
        ]

        tender = self._make_mock_tender()

        with patch("src.ingestion.enrichment.get_session") as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "src.ingestion.enrichment.TenderRepository"
            ) as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.find_unenriched.return_value = [tender]
                mock_repo_cls.return_value = mock_repo

                pipeline = EnrichmentPipeline(client=client)
                result = await pipeline.run(limit=10)

                assert result.succeeded == 1
                assert result.failed == 0
                mock_repo.update_enrichment.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_ollama_unavailable(self) -> None:
        client = AsyncMock(spec=OllamaClient)
        client.is_available.return_value = False

        pipeline = EnrichmentPipeline(client=client)
        result = await pipeline.run()

        assert result.succeeded == 0
        assert result.processed == 0

    @pytest.mark.asyncio
    async def test_continues_on_individual_failure(self) -> None:
        client = AsyncMock(spec=OllamaClient)
        client.is_available.return_value = True
        client.generate.side_effect = [
            LLMError("fail"),  # summary for tender1
            # no searchable needed since summary failed
        ]

        tender = self._make_mock_tender()

        with patch("src.ingestion.enrichment.get_session") as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "src.ingestion.enrichment.TenderRepository"
            ) as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.find_unenriched.return_value = [tender]
                mock_repo_cls.return_value = mock_repo

                pipeline = EnrichmentPipeline(client=client)
                result = await pipeline.run(limit=10)

                assert result.failed == 1
                assert result.succeeded == 0
                assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_truncates_long_output(self) -> None:
        client = AsyncMock(spec=OllamaClient)
        client.is_available.return_value = True
        client.generate.side_effect = [
            "x" * 500,  # summary > MAX_SUMMARY_LEN
            "y" * 5000,  # searchable > MAX_SEARCHABLE_LEN
        ]

        tender = self._make_mock_tender()

        with patch("src.ingestion.enrichment.get_session") as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "src.ingestion.enrichment.TenderRepository"
            ) as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.find_unenriched.return_value = [tender]
                mock_repo_cls.return_value = mock_repo

                pipeline = EnrichmentPipeline(client=client)
                result = await pipeline.run(limit=10)

                assert result.succeeded == 1
                call_args = mock_repo.update_enrichment.call_args
                summary = call_args[1]["summary"]
                searchable = call_args[1]["searchable_text"]
                assert len(summary) == MAX_SUMMARY_LEN
                assert len(searchable) == MAX_SEARCHABLE_LEN

    @pytest.mark.asyncio
    async def test_no_unenriched_tenders(self) -> None:
        client = AsyncMock(spec=OllamaClient)
        client.is_available.return_value = True

        with patch("src.ingestion.enrichment.get_session") as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "src.ingestion.enrichment.TenderRepository"
            ) as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.find_unenriched.return_value = []
                mock_repo_cls.return_value = mock_repo

                pipeline = EnrichmentPipeline(client=client)
                result = await pipeline.run()

                assert result.processed == 0
                assert result.succeeded == 0
