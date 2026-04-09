from __future__ import annotations

import asyncio
import logging

from app.stream.macropulse.ingestion.api.routes.hitl import router
from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
from app.stream.macropulse.ingestion.models.alerts import Alert
from app.stream.macropulse.ingestion.models.hitl_queue import HITLQueue

logger = logging.getLogger(__name__)


def should_route_to_hitl(confidence: float, publish_status: str) -> bool:
    return publish_status == "hitl_queue" or confidence < 0.7


async def _enqueue_async(
    query: str,
    query_type: str,
    impact: str,
    confidence: float,
    publish_status: str,
    region: str | None = None,
    tenant_id: str | None = None,
) -> None:
    if not should_route_to_hitl(confidence, publish_status):
        return

    tenant = tenant_id or "default"
    reason = f"Low confidence {confidence:.2f} for {query_type}"
    source_citation = region or "macropulse"

    try:
        async with AsyncSessionLocal() as session:
            alert = Alert(
                tenant_id=tenant,
                alert_type="hitl_queue",
                tier="P2",
                title=f"HITL Review Required - {query_type}",
                body=query,
                source_citation=source_citation,
                confidence_score=confidence,
                financial_impact_cr=None,
                macro_variable=impact or "unspecified",
                status="hitl_queued",
            )
            session.add(alert)
            await session.flush()

            session.add(
                HITLQueue(
                    alert_id=alert.id,
                    tenant_id=tenant,
                    reason=reason,
                )
            )
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to enqueue HITL item: %s", exc)


def enqueue_for_hitl(
    query: str,
    query_type: str,
    impact: str,
    confidence: float,
    publish_status: str,
    region: str | None = None,
    tenant_id: str | None = None,
) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(
        _enqueue_async(
            query=query,
            query_type=query_type,
            impact=impact,
            confidence=confidence,
            publish_status=publish_status,
            region=region,
            tenant_id=tenant_id,
        )
    )
