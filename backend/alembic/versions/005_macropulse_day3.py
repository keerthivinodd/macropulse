"""Add MacroPulse Day 3 fields and tenant profiles table.

Revision ID: 005_macropulse_day3
Revises: 004
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "005_macropulse_day3"
down_revision = "005_macropulse_bootstrap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("macro_rates") as batch_op:
        batch_op.add_column(sa.Column("saibor_3m_pct", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("saibor_6m_pct", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("eibor_1m_pct", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("eibor_3m_pct", sa.Float(), nullable=True))

    op.create_table(
        "tenant_profiles",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("profile_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id"),
    )


def downgrade() -> None:
    op.drop_table("tenant_profiles")
    with op.batch_alter_table("macro_rates") as batch_op:
        batch_op.drop_column("eibor_3m_pct")
        batch_op.drop_column("eibor_1m_pct")
        batch_op.drop_column("saibor_6m_pct")
        batch_op.drop_column("saibor_3m_pct")
