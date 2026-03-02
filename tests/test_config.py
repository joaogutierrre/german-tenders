"""Tests for src/config.py."""

import pytest

from src.config import Settings, settings


class TestSettings:
    def test_defaults_loaded(self) -> None:
        """Settings loads with sensible defaults."""
        s = Settings(
            _env_file=None,  # type: ignore[call-arg]
            db_password="test",
            minio_password="test",
        )
        assert s.db_host == "localhost"
        assert s.db_port == 5432
        assert s.db_name == "german_tenders"
        assert s.embedding_dimension == 384
        assert s.ingestion_batch_size == 100

    def test_database_url_async(self) -> None:
        """database_url returns asyncpg connection string."""
        s = Settings(
            _env_file=None,  # type: ignore[call-arg]
            db_user="testuser",
            db_password="testpass",
            db_host="dbhost",
            db_port=5433,
            db_name="testdb",
        )
        assert s.database_url == "postgresql+asyncpg://testuser:testpass@dbhost:5433/testdb"

    def test_database_url_sync(self) -> None:
        """database_url_sync returns psycopg2 connection string."""
        s = Settings(
            _env_file=None,  # type: ignore[call-arg]
            db_user="testuser",
            db_password="testpass",
            db_host="dbhost",
            db_port=5433,
            db_name="testdb",
        )
        assert s.database_url_sync == "postgresql+psycopg2://testuser:testpass@dbhost:5433/testdb"

    def test_embedding_dimension_is_384(self) -> None:
        """Embedding dimension must be 384."""
        assert settings.embedding_dimension == 384

    def test_reads_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings reads from environment variables."""
        monkeypatch.setenv("DB_HOST", "custom-host")
        monkeypatch.setenv("DB_PORT", "9999")
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.db_host == "custom-host"
        assert s.db_port == 9999

    def test_ollama_defaults(self) -> None:
        """Ollama settings have correct defaults."""
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.ollama_base_url == "http://localhost:11434"
        assert s.ollama_model == "gemma3:4b"
