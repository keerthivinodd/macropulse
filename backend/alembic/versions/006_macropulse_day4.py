"""Add MacroPulse Day 4 alerting tables.

Revision ID: 006_macropulse_day4
Revises: 005_macropulse_day3
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "006_macropulse_day4"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_profiles",
        sa.Column("notification_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("tier", sa.String(length=2), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_citation", sa.String(length=255), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("financial_impact_cr", sa.Float(), nullable=True),
        sa.Column("macro_variable", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_tenant_id", "alerts", ["tenant_id"])
    op.create_index("ix_alerts_status", "alerts", ["status"])

    op.create_table(
        "hitl_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("assigned_to", sa.String(length=128), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hitl_queue_tenant_id", "hitl_queue", ["tenant_id"])

    op.create_table(
        "guardrail_violations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("alert_title", sa.String(length=255), nullable=True),
        sa.Column("source_citation", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guardrail_violations_tenant_id", "guardrail_violations", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_guardrail_violations_tenant_id", table_name="guardrail_violations")
    op.drop_table("guardrail_violations")
    op.drop_index("ix_hitl_queue_tenant_id", table_name="hitl_queue")
    op.drop_table("hitl_queue")
    op.drop_index("ix_alerts_status", table_name="alerts")
    op.drop_index("ix_alerts_tenant_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_column("tenant_profiles", "notification_config")
