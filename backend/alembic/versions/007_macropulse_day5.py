"""Add MacroPulse Day 5 dashboard and residency support tables.

Revision ID: 007_macropulse_day5
Revises: 006_macropulse_day4
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "007_macropulse_day5"
down_revision = "006_macropulse_day4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "residency_violations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("attempted_write_region", sa.String(length=16), nullable=False),
        sa.Column("correct_region", sa.String(length=16), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_residency_violations_tenant_id", "residency_violations", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_residency_violations_tenant_id", table_name="residency_violations")
    op.drop_table("residency_violations")
