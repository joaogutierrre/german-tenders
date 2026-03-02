"""Initial schema with all 6 tables.

Revision ID: 001
Revises: None
Create Date: 2026-03-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Issuers
    op.create_table(
        "issuers",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("contact_email", sa.String(200), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("nuts_code", sa.String(20), nullable=True),
        sa.Column("org_identifier", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_identifier"),
    )

    # Tenders
    op.create_table(
        "tenders",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", sa.String(200), nullable=True),
        sa.Column("contract_number", sa.String(100), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("cpv_codes", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("estimated_value", sa.Numeric(15, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("award_criteria", sa.JSON(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("submission_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_timeline", sa.String(200), nullable=True),
        sa.Column("execution_location", sa.Text(), nullable=True),
        sa.Column("nuts_codes", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("contract_type", sa.String(50), nullable=True),
        sa.Column("eu_funded", sa.Boolean(), nullable=True),
        sa.Column("renewable", sa.Boolean(), nullable=True),
        sa.Column("lots_count", sa.Integer(), nullable=True),
        sa.Column("max_lots_per_bidder", sa.Integer(), nullable=True),
        sa.Column("platform_url", sa.Text(), nullable=True),
        sa.Column("document_portal_url", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.String(300), nullable=True),
        sa.Column("ai_searchable_text", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("issuer_id", sa.Uuid(), sa.ForeignKey("issuers.id"), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenders_source_id", "tenders", ["source_id"], unique=True)
    op.create_index("ix_tenders_contract_number", "tenders", ["contract_number"])
    op.create_index("ix_tenders_cpv_codes", "tenders", ["cpv_codes"], postgresql_using="gin")
    op.create_index("ix_tenders_nuts_codes", "tenders", ["nuts_codes"], postgresql_using="gin")
    op.create_index("ix_tenders_submission_deadline", "tenders", ["submission_deadline"])
    op.create_index("ix_tenders_publication_date", "tenders", ["publication_date"])

    # Organizations
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tax_id", sa.String(20), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("website_resolved", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("industry_keywords", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_tax_id", "organizations", ["tax_id"], unique=True)

    # Tender Lots
    op.create_table(
        "tender_lots",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tender_id", sa.Uuid(), sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lot_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("estimated_value", sa.Numeric(15, 2), nullable=True),
        sa.Column("cpv_codes", sa.ARRAY(sa.String()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Tender Documents
    op.create_table(
        "tender_documents",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tender_id", sa.Uuid(), sa.ForeignKey("tenders.id"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("storage_bucket", sa.String(100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Match Results
    op.create_table(
        "match_results",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("tender_id", sa.Uuid(), sa.ForeignKey("tenders.id"), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("matched_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("match_results")
    op.drop_table("tender_documents")
    op.drop_table("tender_lots")
    op.drop_table("organizations")
    op.drop_table("tenders")
    op.drop_table("issuers")
    op.execute("DROP EXTENSION IF EXISTS vector")
