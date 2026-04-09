from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.stream.macropulse.ingestion.api.guardrails_runtime import (
    GuardrailError,
    redact_pii,
    validate_sources,
)
from app.stream.macropulse.ingestion.api.notification_tool import NotificationTool
from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
from app.stream.macropulse.ingestion.models.alerts import Alert
from app.stream.macropulse.ingestion.models.hitl_queue import HITLQueue
from app.stream.macropulse.ingestion.models.tenant_profile import TenantProfileModel
from app.stream.macropulse.ingestion.schemas.alerts import AlertResponse, ClassifyAlertRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _derive_tier(agent_output: dict[str, Any]) -> str:
    macro_variable = agent_output.get("macro_variable", "")

    if macro_variable in {"repo_rate", "mpc_decision", "sama_policy", "cbuae_policy"}:
        return "P1"
    if agent_output.get("anomaly_z_score", 0) > 3.0 and macro_variable in {"fx_usd_inr", "repo_rate"}:
        return "P1"
    if agent_output.get("sanctions_match") is True:
        return "P1"

    if macro_variable == "cpi_wpi" and abs(agent_output.get("deviation_from_consensus_bps", 0)) >= 50:
        return "P2"
    if macro_variable == "gsec_yield" and abs(agent_output.get("change_bps", 0)) >= 25:
        return "P2"
    if macro_variable == "fx_usd_inr" and abs(agent_output.get("change_pct_24h", 0)) >= 2.0:
        return "P2"

    if macro_variable in {"crude_oil", "commodity"} and 3.0 <= abs(agent_output.get("change_pct_5d", 0)) <= 10.0:
        return "P3"
    if macro_variable == "pmi" and abs(agent_output.get("delta_from_prior", 0)) > 2.0:
        return "P3"

    return "P3"


def _derive_status(confidence_score: float) -> str | None:
    if confidence_score >= 0.85:
        return "pending"
    if 0.70 <= confidence_score < 0.85:
        return "hitl_queued"
    return None


async def _get_tenant_notification_config(session, tenant_id: str) -> dict[str, Any]:
    row = await session.get(TenantProfileModel, tenant_id)
    if not row or row.is_deleted:
        return {}
    return row.notification_config or row.profile_data.get("notification_config", {})


async def classify_alert(agent_output: dict[str, Any], tenant_id: str) -> Alert | None:
    confidence_score = float(agent_output.get("confidence_score", 0.0))
    status = _derive_status(confidence_score)
    if status is None:
        logger.info("Dropping low-confidence alert for tenant=%s confidence=%.2f", tenant_id, confidence_score)
        return None

    title = redact_pii(agent_output.get("title", "MacroPulse Alert"))
    body = redact_pii(agent_output.get("body", ""))
    source_citation = agent_output.get("source_citation", "")

    await validate_sources(tenant_id=tenant_id, title=title, source_citation=source_citation)

    alert = Alert(
        tenant_id=tenant_id,
        alert_type=agent_output.get("alert_type", "macro_signal"),
        tier=_derive_tier(agent_output),
        title=title,
        body=body,
        source_citation=source_citation,
        confidence_score=confidence_score,
        financial_impact_cr=agent_output.get("financial_impact_cr"),
        macro_variable=agent_output.get("macro_variable", "unknown"),
        status=status,
    )

    async with AsyncSessionLocal() as session:
        session.add(alert)
        await session.flush()

        if status == "hitl_queued":
            session.add(
                HITLQueue(
                    alert_id=alert.id,
                    tenant_id=tenant_id,
                    reason=f"confidence_below_threshold ({confidence_score:.2f})",
                )
            )

        await session.commit()
        await session.refresh(alert)

        tenant_config = await _get_tenant_notification_config(session, tenant_id)

    notifier = NotificationTool()

    if status == "pending":
        dispatch_result = await notifier.dispatch(alert, tenant_config)
        if alert.tier == "P1":
            async with AsyncSessionLocal() as session:
                persisted = await session.get(Alert, alert.id)
                if persisted:
                    persisted.status = "dispatched"
                    persisted.dispatched_at = datetime.now(timezone.utc)
                    await session.commit()
                    await session.refresh(persisted)
                    return persisted
        return alert

    if status == "hitl_queued":
        analyst_alert = Alert(
            tenant_id=tenant_id,
            alert_type="hitl_queue",
            tier="P2",
            title=f"New alert pending review: {title}",
            body=body,
            source_citation=source_citation,
            confidence_score=confidence_score,
            financial_impact_cr=agent_output.get("financial_impact_cr"),
            macro_variable=alert.macro_variable,
            status="pending",
        )
        await notifier.dispatch(analyst_alert, tenant_config)

    return alert


@router.post(
    "/classify",
    response_model=AlertResponse | None,
    summary="Classify and persist a MacroPulse alert",
    description="Classifies agent output into P1/P2/P3, applies guardrails, stores the alert, and routes it to dispatch or HITL.",
)
async def classify_alert_route(payload: ClassifyAlertRequest) -> AlertResponse | None:
    try:
        alert = await classify_alert(payload.agent_output, payload.tenant_id)
    except GuardrailError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if alert is None:
        return None
    return AlertResponse.from_orm_alert(alert)


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert by ID",
    description="Returns a persisted alert by identifier.",
)
async def get_alert(alert_id: str) -> AlertResponse:
    alert_uuid = uuid.UUID(alert_id)
    async with AsyncSessionLocal() as session:
        alert = await session.get(Alert, alert_uuid)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return AlertResponse.from_orm_alert(alert)
