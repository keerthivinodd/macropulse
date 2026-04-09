"""
Day 4 tests — Alert engine, HITL queue, Novu dispatch, PII redaction, guardrails.
Run: pytest backend/app/stream/macropulse/ingestion/tests/test_day4.py -v
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.stream.macropulse.ingestion.api.alert_engine import _derive_tier, _derive_status
from app.stream.macropulse.ingestion.api.guardrails_runtime import (
    GuardrailError,
    redact_pii,
    validate_sources,
)
from app.stream.macropulse.ingestion.models.alerts import Alert


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_alert(**kwargs) -> Alert:
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id="test-tenant",
        alert_type="macro_signal",
        tier="P1",
        title="RBI cuts repo rate by 25bps",
        body="The RBI MPC voted to reduce the repo rate.",
        source_citation="RBI Bulletin • 2026-04-01T09:30:00+05:30",
        confidence_score=0.92,
        financial_impact_cr=1.5,
        macro_variable="repo_rate",
        status="pending",
        created_at=datetime.now(timezone.utc),
        dispatched_at=None,
    )
    defaults.update(kwargs)
    alert = MagicMock(spec=Alert)
    for k, v in defaults.items():
        setattr(alert, k, v)
    return alert


# ---------------------------------------------------------------------------
# 1. P1 classification — repo_rate → tier="P1"
# ---------------------------------------------------------------------------

def test_p1_classification_rbi_policy():
    agent_output = {
        "macro_variable": "repo_rate",
        "confidence_score": 0.92,
        "title": "RBI cuts repo rate",
        "body": "MPC voted to cut.",
        "source_citation": "RBI Bulletin • 2026-04-01T09:30:00+05:30",
    }
    tier = _derive_tier(agent_output)
    assert tier == "P1", f"Expected P1, got {tier}"


def test_p1_classification_mpc_decision():
    assert _derive_tier({"macro_variable": "mpc_decision"}) == "P1"


def test_p1_classification_high_z_score():
    assert _derive_tier({"macro_variable": "fx_usd_inr", "anomaly_z_score": 3.5}) == "P1"


def test_p2_classification_gsec_yield():
    assert _derive_tier({"macro_variable": "gsec_yield", "change_bps": 30}) == "P2"


def test_p3_classification_crude():
    assert _derive_tier({"macro_variable": "crude_oil", "change_pct_5d": 5.0}) == "P3"


# ---------------------------------------------------------------------------
# 2. HITL routing — confidence=0.72 → status="hitl_queued"
# ---------------------------------------------------------------------------

def test_hitl_routing_low_confidence():
    status = _derive_status(0.72)
    assert status == "hitl_queued"


def test_high_confidence_pending():
    assert _derive_status(0.90) == "pending"


def test_very_low_confidence_dropped():
    assert _derive_status(0.50) is None


# ---------------------------------------------------------------------------
# 3. HITL approve triggers dispatch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hitl_approve_triggers_dispatch():
    alert = _make_alert(status="hitl_queued", tier="P1")
    hitl_item = MagicMock()
    hitl_item.decision = None

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.get = AsyncMock(side_effect=[alert, alert])
    mock_session.execute = AsyncMock(return_value=MagicMock(
        scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=hitl_item)))
    ))
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    dispatch_called = []

    async def mock_dispatch(a, config):
        dispatch_called.append(a)
        return {"dispatch_latency_ms": 50}

    with patch(
        "app.stream.macropulse.ingestion.api.routes.hitl.AsyncSessionLocal",
        return_value=mock_session,
    ), patch(
        "app.stream.macropulse.ingestion.api.routes.hitl.NotificationTool"
    ) as MockNotifier, patch(
        "app.stream.macropulse.ingestion.api.routes.hitl._get_tenant_notification_config",
        new_callable=AsyncMock,
        return_value={},
    ):
        MockNotifier.return_value.dispatch = mock_dispatch
        from app.stream.macropulse.ingestion.api.routes.hitl import approve_hitl
        from app.stream.macropulse.ingestion.schemas.alerts import HITLDecisionRequest

        result = await approve_hitl(
            str(alert.id),
            HITLDecisionRequest(reviewer="analyst@fidelis.com", notes="Verified"),
        )

    assert len(dispatch_called) >= 1
    assert hitl_item.decision == "approved"


# ---------------------------------------------------------------------------
# 4. P1 dispatch latency < 60,000ms
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_p1_dispatch_under_60s():
    from app.stream.macropulse.ingestion.api.notification_tool import NotificationTool

    alert = _make_alert(tier="P1")
    tenant_config = {
        "channels": ["email"],
        "email": "cfo@test.com",
    }

    async def mock_send_email(email, a):
        return {"channel": "email", "status": "sent"}

    notifier = NotificationTool()
    notifier._send_email = mock_send_email

    result = await notifier.dispatch(alert, tenant_config)

    assert result["dispatch_latency_ms"] < 60_000, (
        f"P1 dispatch took {result['dispatch_latency_ms']}ms — exceeds 60s SLO"
    )


# ---------------------------------------------------------------------------
# 5. PII redaction removes PERSON entities
# ---------------------------------------------------------------------------

def test_pii_redaction_removes_names():
    text = "CEO John Smith said the repo rate decision was expected."
    result = redact_pii(text)
    assert "John Smith" not in result
    assert "[PERSON REDACTED]" in result


def test_pii_redaction_no_false_positives():
    text = "The RBI MPC voted to cut the repo rate by 25bps."
    result = redact_pii(text)
    assert "RBI" in result
    assert "repo rate" in result


# ---------------------------------------------------------------------------
# 6. Hallucination guardrail blocks unsourced alerts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hallucination_guardrail_blocks_unsourced():
    with patch(
        "app.stream.macropulse.ingestion.api.guardrails_runtime.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(
            add=MagicMock(), commit=AsyncMock()
        )), __aexit__=AsyncMock(return_value=False)),
    ):
        with pytest.raises(GuardrailError, match="Missing source citation"):
            await validate_sources(
                tenant_id="test-tenant",
                title="RBI cuts rate",
                source_citation="",
            )


@pytest.mark.asyncio
async def test_hallucination_guardrail_blocks_malformed_source():
    with patch(
        "app.stream.macropulse.ingestion.api.guardrails_runtime.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(
            add=MagicMock(), commit=AsyncMock()
        )), __aexit__=AsyncMock(return_value=False)),
    ):
        with pytest.raises(GuardrailError):
            await validate_sources(
                tenant_id="test-tenant",
                title="RBI cuts rate",
                source_citation="RBI Bulletin without timestamp",
            )


@pytest.mark.asyncio
async def test_hallucination_guardrail_passes_valid_source():
    result = await validate_sources(
        tenant_id="test-tenant",
        title="RBI cuts rate",
        source_citation="RBI Bulletin • 2026-04-01T09:30:00+05:30",
    )
    assert result is True
