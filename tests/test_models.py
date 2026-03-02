"""Tests for src/db/models.py — model instantiation and relationships."""

from uuid import UUID

from src.db.models import (
    Issuer,
    MatchResult,
    Organization,
    Tender,
    TenderDocument,
    TenderLot,
)


class TestIssuer:
    def test_create_with_required_fields(self, sample_issuer_data: dict) -> None:
        issuer = Issuer(**sample_issuer_data)
        assert issuer.name == "Stadt Berlin"
        assert issuer.contact_email == "vergabe@berlin.de"

    def test_optional_fields(self) -> None:
        issuer = Issuer(name="Test Issuer")
        assert issuer.contact_email is None
        assert issuer.org_identifier is None

    def test_repr(self) -> None:
        issuer = Issuer(name="Test Issuer")
        assert "Test Issuer" in repr(issuer)


class TestTender:
    def test_create_with_required_fields(self, sample_tender_data: dict) -> None:
        tender = Tender(**sample_tender_data)
        assert tender.title == "IT Infrastructure Maintenance for Berlin Public Schools"
        assert tender.cpv_codes == ["72000000"]
        assert tender.currency == "EUR"

    def test_optional_fields_default_none(self) -> None:
        tender = Tender(title="Test")
        assert tender.estimated_value is None
        assert tender.submission_deadline is None
        assert tender.ai_summary is None
        assert tender.issuer_id is None

    def test_repr(self) -> None:
        tender = Tender(title="A very long tender title that should be truncated in repr")
        assert "Tender" in repr(tender)


class TestOrganization:
    def test_create_with_required_fields(self, sample_organization_data: dict) -> None:
        org = Organization(**sample_organization_data)
        assert org.tax_id == "DE123456789"
        assert org.name == "TechCorp GmbH"
        assert org.website == "https://techcorp.de"

    def test_optional_fields(self) -> None:
        org = Organization(tax_id="DE000000002", name="Org2")
        assert org.website is None
        assert org.description is None

    def test_repr(self) -> None:
        org = Organization(tax_id="DE123456789", name="TechCorp")
        assert "TechCorp" in repr(org)


class TestTenderLot:
    def test_create_with_required_fields(self) -> None:
        from uuid import uuid4

        tid = uuid4()
        lot = TenderLot(tender_id=tid, lot_number=1)
        assert lot.lot_number == 1
        assert lot.tender_id == tid

    def test_optional_fields(self) -> None:
        from uuid import uuid4

        lot = TenderLot(tender_id=uuid4(), lot_number=2, title="Lot 2")
        assert lot.title == "Lot 2"
        assert lot.description is None


class TestTenderDocument:
    def test_create_with_required_fields(self) -> None:
        from datetime import datetime
        from uuid import uuid4

        doc = TenderDocument(
            tender_id=uuid4(),
            filename="specs.pdf",
            storage_key="tender-123/specs.pdf",
            storage_bucket="tender-documents",
            downloaded_at=datetime.now(),
        )
        assert doc.filename == "specs.pdf"
        assert doc.storage_bucket == "tender-documents"


class TestMatchResult:
    def test_create_with_required_fields(self) -> None:
        from uuid import uuid4

        result = MatchResult(
            organization_id=uuid4(),
            tender_id=uuid4(),
            query_text="IT consulting Germany",
            similarity_score=0.85,
        )
        assert result.similarity_score == 0.85
        assert result.query_text == "IT consulting Germany"

    def test_repr(self) -> None:
        from uuid import uuid4

        result = MatchResult(
            organization_id=uuid4(),
            tender_id=uuid4(),
            query_text="test",
            similarity_score=0.923,
        )
        assert "0.923" in repr(result)
