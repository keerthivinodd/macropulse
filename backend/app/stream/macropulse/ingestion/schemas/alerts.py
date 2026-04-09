"""
Pydantic v2 schemas for Alert, HITL queue, and classify endpoint.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ClassifyAlertRequest(BaseModel):
    tenant_id: str
    agent_output: dict[str, Any]


class AlertResponse(BaseModel):
    id: str
    tenant_id: str
    alert_type: str
    tier: str
    title: str
    body: str
    source_citation: str
    confidence_score: float
    financial_impact_cr: float | None = None
    macro_variable: str
    status: str
    created_at: datetime
    dispatched_at: datetime | None = None

    @classmethod
    def from_orm_alert(cls, alert) -> "AlertResponse":
        return cls(
            id=str(alert.id),
            tenant_id=alert.tenant_id,
            alert_type=alert.alert_type,
            tier=alert.tier,
            title=alert.title,
            body=alert.body,
            source_citation=alert.source_citation,
            confidence_score=alert.confidence_score,
            financial_impact_cr=alert.financial_impact_cr,
            macro_variable=alert.macro_variable,
            status=alert.status,
            created_at=alert.created_at,
            dispatched_at=alert.dispatched_at,
        )


class HITLPendingAlert(BaseModel):
    alert_id: str
    tenant_id: str
    title: str
    body: str
    confidence_score: float
    source_citation: str
    reason: str
    created_at: datetime

    @classmethod
    def model_validate(cls, obj, **kwargs):
        if hasattr(obj, "alert_id") and isinstance(obj.alert_id, uuid.UUID):
            obj = obj.__dict__.copy()
            obj["alert_id"] = str(obj["alert_id"])
        return super().model_validate(obj, **kwargs)


class HITLDecisionRequest(BaseModel):
    reviewer: str
    notes: str = ""


class HITLRejectRequest(BaseModel):
    reviewer: str
    notes: str = ""
    reason: str
