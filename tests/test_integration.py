"""Integration tests against real PostgreSQL (requires Docker).

Run with: pytest tests/test_integration.py -v -m integration
Auto-skipped if DB is not available.
"""

from pathlib import Path
from uuid import uuid4

import pytest

from tests.conftest import skipif_no_db

pytestmark = [pytest.mark.integration, skipif_no_db]


# ── Repository: Issuer ─────────────────────────────────────────

class TestIssuerRepository:
    @pytest.mark.asyncio
    async def test_upsert_creates_new(self, db_session) -> None:
        from src.db.repositories import IssuerRepository

        repo = IssuerRepository(db_session)
        issuer = await repo.upsert(
            name="Stadt München",
            org_identifier="DE-MUENCHEN-001",
            contact_email="vergabe@muenchen.de",
        )

        assert issuer.name == "Stadt München"
        assert issuer.org_identifier == "DE-MUENCHEN-001"
        assert issuer.id is not None

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, db_session) -> None:
        from src.db.repositories import IssuerRepository

        repo = IssuerRepository(db_session)
        issuer1 = await repo.upsert(name="Stadt Hamburg", org_identifier="DE-HH-001")
        issuer2 = await repo.upsert(
            name="Stadt Hamburg",
            org_identifier="DE-HH-001",
            contact_email="new@hamburg.de",
        )

        assert issuer1.id == issuer2.id
        assert issuer2.contact_email == "new@hamburg.de"


# ── Repository: Organization ──────────────────────────────────

class TestOrganizationRepository:
    @pytest.mark.asyncio
    async def test_upsert_creates_new(self, db_session) -> None:
        from src.db.repositories import OrganizationRepository

        repo = OrganizationRepository(db_session)
        org, is_new = await repo.upsert(
            tax_id="DE999888777", name="Test GmbH", website="https://test.de"
        )

        assert is_new is True
        assert org.tax_id == "DE999888777"
        assert org.name == "Test GmbH"
        assert org.id is not None

    @pytest.mark.asyncio
    async def test_upsert_existing_returns_false(self, db_session) -> None:
        from src.db.repositories import OrganizationRepository

        repo = OrganizationRepository(db_session)
        org1, new1 = await repo.upsert(
            tax_id="DE111222333", name="First Name"
        )
        org2, new2 = await repo.upsert(
            tax_id="DE111222333", name="Updated Name"
        )

        assert new1 is True
        assert new2 is False
        assert org1.id == org2.id
        assert org2.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_count(self, db_session) -> None:
        from src.db.repositories import OrganizationRepository

        repo = OrganizationRepository(db_session)
        initial = await repo.count()

        await repo.upsert(tax_id="DE444555666", name="Count Test")
        await db_session.flush()

        final = await repo.count()
        assert final == initial + 1


# ── Repository: Tender ─────────────────────────────────────────

class TestTenderRepository:
    @pytest.mark.asyncio
    async def test_upsert_from_raw_creates_new(self, db_session) -> None:
        from src.db.repositories import TenderRepository
        from src.ingestion.parser import RawTenderRecord

        repo = TenderRepository(db_session)
        record = RawTenderRecord(
            notice_id="TEST-001",
            notice_version="1",
            title="Test Tender for Integration",
            cpv_codes=["72000000", "48000000"],
            nuts_codes=["DE300"],
            contract_type="services",
            publication_date=None,
        )

        tender = await repo.upsert_from_raw(record)

        assert tender.id is not None
        assert tender.title == "Test Tender for Integration"
        assert tender.source_id == "TEST-001-1"
        assert tender.cpv_codes == ["72000000", "48000000"]

    @pytest.mark.asyncio
    async def test_upsert_from_raw_updates_existing(self, db_session) -> None:
        from src.db.repositories import TenderRepository
        from src.ingestion.parser import RawTenderRecord

        repo = TenderRepository(db_session)
        record1 = RawTenderRecord(
            notice_id="TEST-UPDATE",
            notice_version="1",
            title="Original Title",
        )
        tender1 = await repo.upsert_from_raw(record1)
        await db_session.flush()

        record2 = RawTenderRecord(
            notice_id="TEST-UPDATE",
            notice_version="1",
            title="Updated Title",
        )
        tender2 = await repo.upsert_from_raw(record2)

        assert tender1.id == tender2.id
        assert tender2.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_find_unenriched(self, db_session) -> None:
        from src.db.repositories import TenderRepository
        from src.ingestion.parser import RawTenderRecord

        repo = TenderRepository(db_session)

        # Create a tender without AI summary
        record = RawTenderRecord(
            notice_id="TEST-UNENRICHED",
            notice_version="1",
            title="Unenriched Tender",
        )
        await repo.upsert_from_raw(record)
        await db_session.flush()

        unenriched = await repo.find_unenriched(limit=100)
        ids = [t.source_id for t in unenriched]
        assert "TEST-UNENRICHED-1" in ids

    @pytest.mark.asyncio
    async def test_update_enrichment(self, db_session) -> None:
        from src.db.repositories import TenderRepository
        from src.ingestion.parser import RawTenderRecord

        repo = TenderRepository(db_session)
        record = RawTenderRecord(
            notice_id="TEST-ENRICH",
            notice_version="1",
            title="To Be Enriched",
        )
        tender = await repo.upsert_from_raw(record)
        await db_session.flush()

        await repo.update_enrichment(
            tender.id,
            summary="Short summary",
            searchable_text="Rich searchable text with keywords",
        )
        await db_session.flush()

        # Re-fetch
        found = await repo.find_by_id(tender.id)
        assert found is not None
        assert found.ai_summary == "Short summary"
        assert found.ai_searchable_text == "Rich searchable text with keywords"

    @pytest.mark.asyncio
    async def test_tender_with_lots(self, db_session) -> None:
        from src.db.repositories import TenderRepository
        from src.ingestion.parser import RawLotRecord, RawTenderRecord

        repo = TenderRepository(db_session)
        record = RawTenderRecord(
            notice_id="TEST-LOTS",
            notice_version="1",
            title="Tender With Lots",
            lots=[
                RawLotRecord(lot_number=1, lot_identifier="LOT-1", title="Lot 1"),
                RawLotRecord(lot_number=2, lot_identifier="LOT-2", title="Lot 2"),
            ],
        )
        tender = await repo.upsert_from_raw(record)
        await db_session.flush()

        found = await repo.find_by_id(tender.id)
        assert found is not None
        assert len(found.lots) == 2

    @pytest.mark.asyncio
    async def test_count(self, db_session) -> None:
        from src.db.repositories import TenderRepository
        from src.ingestion.parser import RawTenderRecord

        repo = TenderRepository(db_session)
        initial = await repo.count()

        await repo.upsert_from_raw(
            RawTenderRecord(
                notice_id="TEST-COUNT",
                notice_version="1",
                title="Count Test",
            )
        )
        await db_session.flush()

        assert await repo.count() == initial + 1


# ── Repository: MatchResult ────────────────────────────────────

class TestMatchResultRepository:
    @pytest.mark.asyncio
    async def test_save_and_find(self, db_session) -> None:
        from src.db.repositories import (
            MatchResultRepository,
            OrganizationRepository,
            TenderRepository,
        )
        from src.ingestion.parser import RawTenderRecord

        # Create org and tender first
        org_repo = OrganizationRepository(db_session)
        org, _ = await org_repo.upsert(tax_id="DE777888999", name="Match Org")

        tender_repo = TenderRepository(db_session)
        tender = await tender_repo.upsert_from_raw(
            RawTenderRecord(
                notice_id="TEST-MATCH",
                notice_version="1",
                title="Match Target",
            )
        )
        await db_session.flush()

        # Save a match
        match_repo = MatchResultRepository(db_session)
        mr = await match_repo.save(
            org_id=org.id,
            tender_id=tender.id,
            query_text="test query",
            score=0.85,
        )
        await db_session.flush()

        assert mr.similarity_score == 0.85

        # Find matches
        matches = await match_repo.find_by_org(org.id)
        assert len(matches) >= 1

    @pytest.mark.asyncio
    async def test_delete_by_org(self, db_session) -> None:
        from src.db.repositories import (
            MatchResultRepository,
            OrganizationRepository,
            TenderRepository,
        )
        from src.ingestion.parser import RawTenderRecord

        org_repo = OrganizationRepository(db_session)
        org, _ = await org_repo.upsert(tax_id="DE555666777", name="Del Org")

        tender_repo = TenderRepository(db_session)
        tender = await tender_repo.upsert_from_raw(
            RawTenderRecord(
                notice_id="TEST-DEL-MATCH",
                notice_version="1",
                title="Del Target",
            )
        )
        await db_session.flush()

        match_repo = MatchResultRepository(db_session)
        await match_repo.save(org.id, tender.id, "q1", 0.5)
        await match_repo.save(org.id, tender.id, "q2", 0.6)
        await db_session.flush()

        deleted = await match_repo.delete_by_org(org.id)
        assert deleted == 2


# ── Full Pipeline with real fixture ───────────────────────────

class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_parse_and_upsert_real_data(self, db_session) -> None:
        """Parse the real CSV fixture and upsert all records to DB."""
        from src.db.repositories import IssuerRepository, TenderRepository
        from src.ingestion.parser import parse_csv_zip

        fixture = Path("tests/fixtures/sample_csv.zip")
        assert fixture.exists()

        records = parse_csv_zip(fixture.read_bytes())
        assert len(records) >= 1200

        tender_repo = TenderRepository(db_session)
        issuer_repo = IssuerRepository(db_session)

        inserted = 0
        for record in records[:50]:  # First 50 to keep test fast
            issuer = None
            if record.issuer_name:
                issuer = await issuer_repo.upsert(
                    name=record.issuer_name,
                    org_identifier=record.issuer_org_identifier,
                )
            tender = await tender_repo.upsert_from_raw(record, issuer)
            inserted += 1

        await db_session.flush()

        count = await tender_repo.count()
        assert count >= 50
