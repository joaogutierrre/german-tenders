"""SQLAlchemy 2.0 ORM models for the German Tenders platform."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all models."""

    pass


class Issuer(Base):
    """Public entity that issues tenders."""

    __tablename__ = "issuers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(200))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)
    nuts_code: Mapped[str | None] = mapped_column(String(20))
    org_identifier: Mapped[str | None] = mapped_column(String(100), unique=True)

    tenders: Mapped[list["Tender"]] = relationship(back_populates="issuer")

    def __repr__(self) -> str:
        return f"<Issuer {self.name!r}>"


class Tender(Base):
    """A public tender notice."""

    __tablename__ = "tenders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[str | None] = mapped_column(
        String(200), unique=True, index=True
    )
    contract_number: Mapped[str | None] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    cpv_codes: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), default=list
    )
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    award_criteria: Mapped[dict | None] = mapped_column(JSON)
    publication_date: Mapped[date | None] = mapped_column(Date)
    submission_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    execution_timeline: Mapped[str | None] = mapped_column(String(200))
    execution_location: Mapped[str | None] = mapped_column(Text)
    nuts_codes: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), default=list
    )
    contract_type: Mapped[str | None] = mapped_column(String(50))
    eu_funded: Mapped[bool | None] = mapped_column(Boolean)
    renewable: Mapped[bool | None] = mapped_column(Boolean)
    lots_count: Mapped[int | None] = mapped_column(Integer)
    max_lots_per_bidder: Mapped[int | None] = mapped_column(Integer)
    platform_url: Mapped[str | None] = mapped_column(Text)
    document_portal_url: Mapped[str | None] = mapped_column(Text)
    ai_summary: Mapped[str | None] = mapped_column(String(300))
    ai_searchable_text: Mapped[str | None] = mapped_column(Text)
    embedding = mapped_column(Vector(384), nullable=True)
    issuer_id: Mapped[UUID | None] = mapped_column(ForeignKey("issuers.id"))
    raw_data: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    issuer: Mapped[Issuer | None] = relationship(back_populates="tenders")
    lots: Mapped[list["TenderLot"]] = relationship(
        back_populates="tender", cascade="all, delete-orphan"
    )
    documents: Mapped[list["TenderDocument"]] = relationship(
        back_populates="tender"
    )
    match_results: Mapped[list["MatchResult"]] = relationship(
        back_populates="tender"
    )

    __table_args__ = (
        Index("ix_tenders_cpv_codes", "cpv_codes", postgresql_using="gin"),
        Index("ix_tenders_nuts_codes", "nuts_codes", postgresql_using="gin"),
        Index("ix_tenders_submission_deadline", "submission_deadline"),
        Index("ix_tenders_publication_date", "publication_date"),
    )

    def __repr__(self) -> str:
        return f"<Tender {self.title[:50]!r}>"


class Organization(Base):
    """A business organization that may bid on tenders."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tax_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    website: Mapped[str | None] = mapped_column(Text)
    website_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    industry_keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    description: Mapped[str | None] = mapped_column(Text)
    embedding = mapped_column(Vector(384), nullable=True)

    match_results: Mapped[list["MatchResult"]] = relationship(
        back_populates="organization"
    )

    __table_args__ = (
        Index("ix_organizations_tax_id", "tax_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name!r} ({self.tax_id})>"


class TenderLot(Base):
    """A lot within a tender."""

    __tablename__ = "tender_lots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tender_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False
    )
    lot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    cpv_codes: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), default=list
    )

    tender: Mapped[Tender] = relationship(back_populates="lots")

    def __repr__(self) -> str:
        return f"<TenderLot #{self.lot_number}>"


class TenderDocument(Base):
    """A document associated with a tender, stored in MinIO."""

    __tablename__ = "tender_documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tender_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenders.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100))
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    tender: Mapped[Tender] = relationship(back_populates="documents")

    def __repr__(self) -> str:
        return f"<TenderDocument {self.filename!r}>"


class MatchResult(Base):
    """Result of matching an organization to a tender via search."""

    __tablename__ = "match_results"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    tender_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenders.id"), nullable=False
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    matched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    organization: Mapped[Organization] = relationship(
        back_populates="match_results"
    )
    tender: Mapped[Tender] = relationship(back_populates="match_results")

    def __repr__(self) -> str:
        return f"<MatchResult score={self.similarity_score:.3f}>"
