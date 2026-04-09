from __future__ import annotations

import logging
import re
from functools import lru_cache

import spacy
from fastapi import APIRouter
from sqlalchemy import desc, select

from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
from app.stream.macropulse.ingestion.models.guardrail_violations import GuardrailViolation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/guardrails", tags=["guardrails"])
SOURCE_CITATION_RE = re.compile(
    r"^.+\s(?:\u2022|\u00b7)\s\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\+\d{2}:\d{2}|Z)$"
)


class GuardrailError(ValueError):
    pass


@lru_cache(maxsize=1)
def _nlp():
    return spacy.load("en_core_web_sm")


def redact_pii(text: str) -> str:
    doc = _nlp()(text or "")
    redacted = text or ""
    for ent in reversed(doc.ents):
        if ent.label_ == "PERSON":
            redacted = redacted[: ent.start_char] + "[PERSON REDACTED]" + redacted[ent.end_char :]
    return redacted


def normalize_source_citation(source_citation: str) -> str:
    normalized = (source_citation or "").strip()
    normalized = normalized.replace("â€¢", "•")
    normalized = re.sub(r"\s\?\s", " • ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


async def log_guardrail_violation(
    tenant_id: str,
    reason: str,
    alert_title: str | None = None,
    source_citation: str | None = None,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            session.add(
                GuardrailViolation(
                    tenant_id=tenant_id,
                    alert_title=alert_title,
                    source_citation=source_citation,
                    reason=reason,
                )
            )
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to persist guardrail violation: %s", exc)


async def validate_sources(*, tenant_id: str, title: str, source_citation: str) -> bool:
    normalized = normalize_source_citation(source_citation)
    if not normalized or not isinstance(source_citation, str) or not SOURCE_CITATION_RE.match(normalized):
        reason = "Missing source citation"
        await log_guardrail_violation(
            tenant_id=tenant_id,
            reason=reason,
            alert_title=title,
            source_citation=normalized or source_citation,
        )
        raise GuardrailError(reason)
    return True


@router.get(
    "/violations/{tenant_id}",
    summary="List guardrail violations",
    description="Returns the audit trail of blocked or malformed alerts for a tenant.",
)
async def get_guardrail_violations(tenant_id: str) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GuardrailViolation)
            .where(GuardrailViolation.tenant_id == tenant_id)
            .order_by(desc(GuardrailViolation.created_at))
        )
        rows = result.scalars().all()

    return [
        {
            "id": str(row.id),
            "tenant_id": row.tenant_id,
            "alert_title": row.alert_title,
            "source_citation": row.source_citation,
            "reason": row.reason,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
