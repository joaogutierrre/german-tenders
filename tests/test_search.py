"""Tests for search and embeddings (Phase 5)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.search.structured import SearchFilters, build_filter_query
from src.search.hybrid import _cosine_similarity


# ── SearchFilters ──────────────────────────────────────────────

class TestSearchFilters:
    def test_no_filters_by_default(self) -> None:
        f = SearchFilters()
        assert not f.has_filters

    def test_cpv_filter_active(self) -> None:
        f = SearchFilters(cpv_codes=["72000000"])
        assert f.has_filters

    def test_nuts_filter_active(self) -> None:
        f = SearchFilters(nuts_codes=["DE212"])
        assert f.has_filters

    def test_value_filter_active(self) -> None:
        f = SearchFilters(min_value=1000)
        assert f.has_filters

    def test_multiple_filters_active(self) -> None:
        f = SearchFilters(cpv_codes=["72000000"], min_value=1000, keyword="IT")
        assert f.has_filters


# ── build_filter_query ─────────────────────────────────────────

class TestBuildFilterQuery:
    def test_no_filters_returns_select(self) -> None:
        stmt = build_filter_query(SearchFilters())
        # Should compile without error
        assert str(stmt) is not None

    def test_cpv_filter_in_query(self) -> None:
        stmt = build_filter_query(SearchFilters(cpv_codes=["72000000"]))
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "cpv_codes" in sql

    def test_nuts_filter_in_query(self) -> None:
        stmt = build_filter_query(SearchFilters(nuts_codes=["DE212"]))
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "nuts_codes" in sql

    def test_value_range_filter(self) -> None:
        stmt = build_filter_query(
            SearchFilters(min_value=1000, max_value=50000)
        )
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "estimated_value" in sql

    def test_keyword_filter(self) -> None:
        stmt = build_filter_query(SearchFilters(keyword="software"))
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "software" in sql.lower()

    def test_contract_type_filter(self) -> None:
        stmt = build_filter_query(SearchFilters(contract_type="services"))
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "contract_type" in sql


# ── Cosine Similarity ──────────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        v = [1.0, 0.0, 0.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(_cosine_similarity(a, b)) < 1e-6

    def test_opposite_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(_cosine_similarity(a, b) - (-1.0)) < 1e-6

    def test_zero_vector_returns_zero(self) -> None:
        a = [0.0, 0.0]
        b = [1.0, 1.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_similar_vectors_high_score(self) -> None:
        a = [0.9, 0.1, 0.0]
        b = [0.8, 0.2, 0.0]
        assert _cosine_similarity(a, b) > 0.9


# ── Embeddings ─────────────────────────────────────────────────

class TestEmbeddings:
    def test_encode_text_returns_384_dim(self) -> None:
        """encode_text returns a 384-dimensional normalized vector."""
        with patch("src.search.embeddings._model", None):
            with patch("src.search.embeddings.SentenceTransformer") as mock_st:
                import numpy as np

                mock_model = MagicMock()
                vec = np.random.randn(384).astype(np.float32)
                vec = vec / np.linalg.norm(vec)
                mock_model.encode.return_value = vec
                mock_st.return_value = mock_model

                from src.search.embeddings import encode_text

                result = encode_text("test query")

                assert len(result) == 384
                # Check normalized (L2 norm ~1)
                norm = sum(x * x for x in result) ** 0.5
                assert abs(norm - 1.0) < 0.01

    def test_encode_batch_returns_list(self) -> None:
        """encode_batch returns a list of 384-dim vectors."""
        with patch("src.search.embeddings._model", None):
            with patch("src.search.embeddings.SentenceTransformer") as mock_st:
                import numpy as np

                mock_model = MagicMock()
                vecs = np.random.randn(3, 384).astype(np.float32)
                for i in range(3):
                    vecs[i] = vecs[i] / np.linalg.norm(vecs[i])
                mock_model.encode.return_value = vecs
                mock_st.return_value = mock_model

                from src.search.embeddings import encode_batch

                results = encode_batch(["a", "b", "c"])

                assert len(results) == 3
                assert all(len(v) == 384 for v in results)
