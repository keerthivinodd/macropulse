"""macropulse kpi warehouse tables

Revision ID: 005
Revises: 004
Create Date: 2026-04-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "005_macropulse_day3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Core KPI time-series table
    op.create_table(
        "macro_kpis",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("metric", sa.String(64), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("region", sa.String(64), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("source", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_macro_kpis_metric_date", "macro_kpis", ["metric", "date"], unique=True)

    # Seed representative rows so kpi_sql_tool returns real data immediately
    op.execute("""
        INSERT INTO macro_kpis (metric, date, value, region, currency, source) VALUES
        ('repo_rate', '2024-04-01', 6.50, 'India', 'INR', 'RBI'),
        ('repo_rate', '2024-06-01', 6.50, 'India', 'INR', 'RBI'),
        ('repo_rate', '2024-08-01', 6.50, 'India', 'INR', 'RBI'),
        ('repo_rate', '2024-10-01', 6.50, 'India', 'INR', 'RBI'),
        ('repo_rate', '2024-12-01', 6.25, 'India', 'INR', 'RBI'),
        ('repo_rate', '2025-02-01', 6.25, 'India', 'INR', 'RBI'),
        ('cpi',       '2024-04-01', 4.83, 'India', 'INR', 'MOSPI'),
        ('cpi',       '2024-06-01', 5.08, 'India', 'INR', 'MOSPI'),
        ('cpi',       '2024-08-01', 3.65, 'India', 'INR', 'MOSPI'),
        ('cpi',       '2024-10-01', 5.49, 'India', 'INR', 'MOSPI'),
        ('cpi',       '2024-12-01', 5.22, 'India', 'INR', 'MOSPI'),
        ('cpi',       '2025-02-01', 4.31, 'India', 'INR', 'MOSPI'),
        ('usd_inr',   '2024-04-01', 83.40, 'India', 'INR', 'RBI'),
        ('usd_inr',   '2024-06-01', 83.52, 'India', 'INR', 'RBI'),
        ('usd_inr',   '2024-08-01', 83.96, 'India', 'INR', 'RBI'),
        ('usd_inr',   '2024-10-01', 83.80, 'India', 'INR', 'RBI'),
        ('usd_inr',   '2024-12-01', 84.70, 'India', 'INR', 'RBI'),
        ('usd_inr',   '2025-02-01', 86.50, 'India', 'INR', 'RBI'),
        ('brent',     '2024-04-01', 87.00, 'Global', 'USD', 'EIA'),
        ('brent',     '2024-06-01', 85.00, 'Global', 'USD', 'EIA'),
        ('brent',     '2024-08-01', 79.50, 'Global', 'USD', 'EIA'),
        ('brent',     '2024-10-01', 74.00, 'Global', 'USD', 'EIA'),
        ('brent',     '2024-12-01', 73.50, 'Global', 'USD', 'EIA'),
        ('brent',     '2025-02-01', 76.00, 'Global', 'USD', 'EIA')
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_index("ix_macro_kpis_metric_date", table_name="macro_kpis")
    op.drop_table("macro_kpis")
