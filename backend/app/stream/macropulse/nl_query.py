from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class NLQueryRequest(BaseModel):
    text: str = Field(..., description="Natural language question from the CFO or finance user")
    tenant_id: str = Field(..., description="Tenant identifier for region/currency context")
    region: str = Field(default="India", description="Primary region context")


class NLQueryResponse(BaseModel):
    query: str
    tenant_id: str
    region: str
    intent: Literal["impact", "confidence", "sources", "recommended_action", "unknown"]
    macro_variables: list[str]
    route: Literal["MarketSignalAgent", "ScenarioEngine", "KPIWarehouse", "Fallback"]
    confidence: float
    sources: list[str]
    recommended_action: str
    generated_at: datetime


_INTENT_KEYWORDS: dict[str, list[str]] = {
    "impact": ["impact", "effect", "affect", "change", "shift", "cost", "margin", "ebitda", "p&l"],
    "confidence": ["confidence", "reliable", "accuracy", "certain", "sure", "probability"],
    "sources": ["source", "data", "where", "from", "feed", "provider"],
    "recommended_action": ["recommend", "suggest", "should", "action", "hedge", "mitigate", "strategy"],
}

_VARIABLE_KEYWORDS: dict[str, list[str]] = {
    "inflation": ["inflation", "cpi", "price", "cost"],
    "interest_rate": ["rate", "repo", "fed", "rbi", "libor", "interest", "yield"],
    "fx": ["fx", "currency", "usd", "inr", "aed", "sar", "exchange", "forex"],
    "commodity": ["oil", "crude", "brent", "commodity", "petroleum", "gold"],
    "gdp": ["gdp", "growth", "economy", "recession"],
}


def _detect_intent(text: str) -> Literal["impact", "confidence", "sources", "recommended_action", "unknown"]:
    lower = text.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return intent  # type: ignore[return-value]
    return "unknown"


def _detect_variables(text: str) -> list[str]:
    lower = text.lower()
    return [var for var, keywords in _VARIABLE_KEYWORDS.items() if any(kw in lower for kw in keywords)]


def _route_query(intent: str, variables: list[str]) -> Literal["MarketSignalAgent", "ScenarioEngine", "KPIWarehouse", "Fallback"]:
    if intent == "impact" or "fx" in variables or "interest_rate" in variables:
        return "ScenarioEngine"
    if intent in ("confidence", "sources"):
        return "KPIWarehouse"
    if variables:
        return "MarketSignalAgent"
    return "Fallback"


def parse_nl_query(request: NLQueryRequest) -> NLQueryResponse:
    intent = _detect_intent(request.text)
    variables = _detect_variables(request.text)
    route = _route_query(intent, variables)

    confidence = 0.82 if variables else 0.55
    if intent != "unknown":
        confidence = min(confidence + 0.08, 0.97)

    sources = []
    if "inflation" in variables:
        sources.append("BLS CPI / RBI CPI")
    if "interest_rate" in variables:
        sources.append("RBI / FED / ECB policy feeds")
    if "fx" in variables:
        sources.append("ECB FX Reference / SAMA FX")
    if "commodity" in variables:
        sources.append("EIA Brent Crude / MOSPI")
    if not sources:
        sources = ["MacroPulse KPI Warehouse"]

    action_map = {
        "impact": f"Run scenario simulation for {', '.join(variables) or 'macro variables'} using ScenarioEngine",
        "confidence": "Review confidence scoring breakdown in MacroPulse confidence module",
        "sources": "Check source registry at /api/v1/macropulse/sources",
        "recommended_action": f"Consult MarketSignal Agent for hedging strategy on {', '.join(variables) or 'current exposure'}",
        "unknown": "Clarify query with more specific macro variable or intent",
    }

    return NLQueryResponse(
        query=request.text,
        tenant_id=request.tenant_id,
        region=request.region,
        intent=intent,
        macro_variables=variables,
        route=route,
        confidence=round(confidence, 2),
        sources=sources,
        recommended_action=action_map[intent],
        generated_at=datetime.now(UTC),
    )
