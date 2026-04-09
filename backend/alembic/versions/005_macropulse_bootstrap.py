"""MacroPulse Day 1-2 bootstrap — create ingestion base tables.

Creates: macro_rates, fx_rates, commodity_prices, news_articles
These tables are required before Day 3 migration can ALTER macro_rates.

Revision ID: 005_macropulse_bootstrap
Revises: 004
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005_macropulse_bootstrap"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── macro_rates ──────────────────────────────────────────────────────────
    op.create_table(
        "macro_rates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("region", sa.String(8), nullable=False, server_default="IN"),
        sa.Column("repo_rate_pct", sa.Float(), nullable=True),
        sa.Column("gsec_10y_yield_pct", sa.Float(), nullable=True),
        sa.Column("cpi_index", sa.Float(), nullable=True),
        sa.Column("wpi_index", sa.Float(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("confidence_tier", sa.String(32), nullable=False, server_default="primary"),
        sa.UniqueConstraint("source", "date", name="uq_macro_rates_source_date"),
    )

    # ── fx_rates ─────────────────────────────────────────────────────────────
    op.create_table(
        "fx_rates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usd_inr", sa.Float(), nullable=True),
        sa.Column("aed_inr", sa.Float(), nullable=True),
        sa.Column("sar_inr", sa.Float(), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("region", sa.String(10), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── commodity_prices ─────────────────────────────────────────────────────
    op.create_table(
        "commodity_prices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("commodity", sa.String(50), nullable=False),
        sa.Column("price_value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(30), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("region", sa.String(10), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── news_articles ─────────────────────────────────────────────────────────
    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.String(2048), nullable=True),
        sa.Column("url", sa.String(1024), nullable=False, unique=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_name", sa.String(128), nullable=True),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("embedded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("url", name="uq_news_articles_url"),
    )


def downgrade() -> None:
    op.drop_table("news_articles")
    op.drop_table("commodity_prices")
    op.drop_table("fx_rates")
    op.drop_table("macro_rates")
