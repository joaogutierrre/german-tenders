"""Centralized configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "german_tenders"
    db_user: str = "app"
    db_password: str = "changeme"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    ollama_model_fast: str = "gemma3:1b"

    # Embeddings
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimension: int = 384

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_user: str = "minioadmin"
    minio_password: str = "changeme"
    minio_bucket: str = "tender-documents"
    minio_exports_bucket: str = "api-exports"

    # Ingestion
    ingestion_batch_size: int = 100
    ingestion_default_days: int = 7
    archive_raw_exports: bool = True

    @property
    def database_url(self) -> str:
        """Async PostgreSQL connection string (asyncpg)."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync PostgreSQL connection string (psycopg2, for Alembic)."""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
