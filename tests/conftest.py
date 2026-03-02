"""Shared test fixtures."""

import pytest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# ── Shared data fixtures ─────────────────────────────────────

@pytest.fixture
def sample_tender_data() -> dict:
    """Minimal data for creating a Tender."""
    return {
        "title": "IT Infrastructure Maintenance for Berlin Public Schools",
        "cpv_codes": ["72000000"],
        "nuts_codes": ["DE300"],
        "currency": "EUR",
        "contract_type": "services",
    }


@pytest.fixture
def sample_issuer_data() -> dict:
    """Minimal data for creating an Issuer."""
    return {
        "name": "Stadt Berlin",
        "contact_email": "vergabe@berlin.de",
        "nuts_code": "DE300",
        "org_identifier": "DE-BERLIN-001",
    }


@pytest.fixture
def sample_organization_data() -> dict:
    """Minimal data for creating an Organization."""
    return {
        "tax_id": "DE123456789",
        "name": "TechCorp GmbH",
        "website": "https://techcorp.de",
    }


# ── Integration fixtures (real PostgreSQL) ───────────────────

def _can_connect_to_db() -> bool:
    """Check if the test database is reachable."""
    try:
        import psycopg2

        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="german_tenders",
            user="app",
            password="changeme",
        )
        conn.close()
        return True
    except Exception:
        return False


# This flag is evaluated once at import time
DB_AVAILABLE = _can_connect_to_db()

# Use this as: @pytest.mark.skipif(not DB_AVAILABLE, reason="PostgreSQL not available")
skipif_no_db = pytest.mark.skipif(
    not DB_AVAILABLE, reason="PostgreSQL not available (docker compose up -d)"
)


@pytest.fixture
async def db_session():
    """Provide a real async DB session with rollback after each test.

    REQUIRES: Docker PostgreSQL running + migrations applied.
    """
    from src.config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        # Each test runs in a transaction that gets rolled back
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()

    await engine.dispose()
