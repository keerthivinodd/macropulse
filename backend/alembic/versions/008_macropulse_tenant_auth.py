"""Add MacroPulse tenant auth fields to users.

Revision ID: 008
Revises: 007_macropulse_day5
Create Date: 2026-04-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "008"
down_revision = "007_macropulse_day5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("tenant_key", sa.String(length=100), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "account_type",
            sa.String(length=50),
            nullable=False,
            server_default="platform_user",
        ),
    )
    op.create_index("ix_users_tenant_key", "users", ["tenant_key"])


def downgrade() -> None:
    op.drop_index("ix_users_tenant_key", table_name="users")
    op.drop_column("users", "account_type")
    op.drop_column("users", "tenant_key")
