from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.stream.macropulse.ingestion.api.alert_engine import _get_tenant_notification_config
from app.stream.macropulse.ingestion.api.notification_tool import NotificationTool
from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
from app.stream.macropulse.ingestion.models.alerts import Alert
from app.stream.macropulse.ingestion.models.hitl_queue import HITLQueue
from app.stream.macropulse.ingestion.schemas.alerts import (
    AlertResponse,
    HITLDecisionRequest,
    HITLPendingAlert,
    HITLRejectRequest,
)

router = APIRouter(prefix="/hitl", tags=["hitl"])


async def _fetch_pending(tenant_id: str | None = None) -> list[HITLPendingAlert]:
    async with AsyncSessionLocal() as session:
        query = (
            select(HITLQueue)
            .options(joinedload(HITLQueue.alert))
            .where(HITLQueue.decision.is_(None))
            .order_by(HITLQueue.created_at.desc())
        )
        if tenant_id:
            query = query.where(HITLQueue.tenant_id == tenant_id)
        result = await session.execute(query)
        rows = result.scalars().all()

    payload: list[HITLPendingAlert] = []
    for row in rows:
        if not row.alert:
            continue
        payload.append(
            HITLPendingAlert(
                alert_id=str(row.alert.id),
                tenant_id=row.tenant_id,
                title=row.alert.title,
                body=row.alert.body,
                confidence_score=row.alert.confidence_score,
                source_citation=row.alert.source_citation,
                reason=row.reason,
                created_at=row.created_at,
            )
        )
    return payload


@router.get(
    "/pending",
    response_model=list[HITLPendingAlert],
    summary="List pending HITL alerts",
    description="Returns all alerts currently queued for human review.",
)
async def get_pending_hitl() -> list[HITLPendingAlert]:
    return await _fetch_pending()


@router.get(
    "/pending/{tenant_id}",
    response_model=list[HITLPendingAlert],
    summary="List tenant HITL alerts",
    description="Returns pending human-in-the-loop alerts for a specific tenant.",
)
async def get_pending_hitl_for_tenant(tenant_id: str) -> list[HITLPendingAlert]:
    return await _fetch_pending(tenant_id)


@router.post(
    "/{alert_id}/approve",
    response_model=AlertResponse,
    summary="Approve a HITL alert",
    description="Approves a queued alert, dispatches it through the notification tool, and marks it dispatched.",
)
async def approve_hitl(alert_id: str, payload: HITLDecisionRequest) -> AlertResponse:
    alert_uuid = uuid.UUID(alert_id)
    async with AsyncSessionLocal() as session:
        alert = await session.get(Alert, alert_uuid)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        result = await session.execute(
            select(HITLQueue).where(HITLQueue.alert_id == alert.id).order_by(HITLQueue.created_at.desc())
        )
        queue_item = result.scalars().first()
        if not queue_item:
            raise HTTPException(status_code=404, detail="HITL queue entry not found")

        queue_item.decision = "approved"
        queue_item.assigned_to = payload.reviewer
        queue_item.reviewer_notes = payload.notes
        queue_item.reviewed_at = datetime.now(timezone.utc)
        alert.status = "approved"
        await session.commit()
        await session.refresh(alert)
        tenant_config = await _get_tenant_notification_config(session, alert.tenant_id)

    notifier = NotificationTool()
    await notifier.dispatch(alert, tenant_config)

    async with AsyncSessionLocal() as session:
        persisted = await session.get(Alert, alert.id)
        if persisted:
            persisted.status = "dispatched"
            persisted.dispatched_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(persisted)
            return AlertResponse.from_orm_alert(persisted)

    raise HTTPException(status_code=500, detail="Failed to update alert dispatch status")


@router.post(
    "/{alert_id}/reject",
    response_model=AlertResponse,
    summary="Reject a HITL alert",
    description="Rejects a queued alert and stores reviewer notes and rejection reason.",
)
async def reject_hitl(alert_id: str, payload: HITLRejectRequest) -> AlertResponse:
    alert_uuid = uuid.UUID(alert_id)
    async with AsyncSessionLocal() as session:
        alert = await session.get(Alert, alert_uuid)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        result = await session.execute(
            select(HITLQueue).where(HITLQueue.alert_id == alert.id).order_by(HITLQueue.created_at.desc())
        )
        queue_item = result.scalars().first()
        if not queue_item:
            raise HTTPException(status_code=404, detail="HITL queue entry not found")

        queue_item.decision = "rejected"
        queue_item.assigned_to = payload.reviewer
        queue_item.reviewer_notes = f"{payload.notes}\nReason: {payload.reason}"
        queue_item.reviewed_at = datetime.now(timezone.utc)
        alert.status = "rejected"
        await session.commit()
        await session.refresh(alert)
        return AlertResponse.from_orm_alert(alert)
