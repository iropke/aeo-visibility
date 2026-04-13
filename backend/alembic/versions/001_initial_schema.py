"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("grade", sa.String(2), nullable=True),
        sa.Column("technical_score", sa.Integer(), nullable=True),
        sa.Column("technical_details", postgresql.JSONB(), nullable=True),
        sa.Column("structured_score", sa.Integer(), nullable=True),
        sa.Column("structured_details", postgresql.JSONB(), nullable=True),
        sa.Column("content_score", sa.Integer(), nullable=True),
        sa.Column("content_details", postgresql.JSONB(), nullable=True),
        sa.Column("authority_score", sa.Integer(), nullable=True),
        sa.Column("authority_details", postgresql.JSONB(), nullable=True),
        sa.Column("visibility_score", sa.Integer(), nullable=True),
        sa.Column("visibility_details", postgresql.JSONB(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("recommendations", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("language", sa.String(5), server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_analysis_domain", "analysis_results", ["domain"])

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("analysis_results.id"), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("report_sent", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_leads_email", "leads", ["email"])


def downgrade() -> None:
    op.drop_index("idx_leads_email")
    op.drop_table("leads")
    op.drop_index("idx_analysis_domain")
    op.drop_table("analysis_results")
