"""Add background_jobs table.

Revision ID: 002
Revises: 001
Create Date: 2026-03-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("params", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_total", sa.Integer(), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("pid", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_background_jobs_status", "background_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_background_jobs_status", table_name="background_jobs")
    op.drop_table("background_jobs")
