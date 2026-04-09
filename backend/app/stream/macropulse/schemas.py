from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MacroPulseIndicator(BaseModel):
    key: str
    symbol: str
    label: str
    value: str
    sub: str
    change: str
    dir: Literal["up", "down", "neutral"]
    source: str
    as_of: datetime


class MacroPulseSourceStatus(BaseModel):
    name: str
    status: Literal["live", "fallback"]
    latency: str
    coverage: str


class MacroPulseSourceCatalogEntry(BaseModel):
    id: str
    category: Literal[
        "central_bank_policy",
        "fx_market_data",
        "commodity_prices",
        "inflation_statistics",
        "news_signal_corpora",
        "premium_optional",
    ]
    name: str
    provider_type: Literal["official", "market", "news", "premium"]
    access: Literal["free", "api_key", "enterprise", "free_key"]
    cadence: Literal["real_time", "5_min", "15_min", "hourly", "daily", "monthly"]
    regions: list[Literal["India", "UAE", "Saudi Arabia", "Global"]]
    url: str
    coverage: str
    notes: str | None = None
    requires_api_key: bool = False
    enabled_for_current_build: bool = True


class MacroPulseSourceCatalogResponse(BaseModel):
    generated_at: datetime
    total_sources: int
    sources: list[MacroPulseSourceCatalogEntry]


class MacroPulseIngestionPlanItem(BaseModel):
    source_id: str
    source_name: str
    cadence: str
    purpose: str
    priority: Literal["P0", "P1", "P2"]
    implementation_status: Literal["active", "planned", "key_required", "premium_blocked"]


class MacroPulseIngestionPlanResponse(BaseModel):
    generated_at: datetime
    current_region: Literal["India", "UAE", "Saudi Arabia"]
    current_currency: Literal["INR", "AED", "SAR"]
    plan: list[MacroPulseIngestionPlanItem]


class MacroPulseRealtimeResponse(BaseModel):
    headline: str
    narrative: str
    anomaly_confidence: float = Field(ge=0, le=100)
    market_confidence_score: float = Field(ge=0, le=10)
    global_sentiment_change: float
    generated_at: datetime
    indicators: list[MacroPulseIndicator]
    sources: list[MacroPulseSourceStatus]


class MacroPulseDashboardTile(BaseModel):
    key: str
    label: str
    value: str
    context: str
    tone: Literal["stable", "watch", "action"]


class MacroPulseDashboardAlert(BaseModel):
    severity: Literal["P1", "P2", "P3"]
    title: str
    message: str
    confidence: float = Field(ge=0, le=100)


class MacroPulseSensitivityRow(BaseModel):
    scenario: Literal["interest_rate", "fx", "commodity", "combined"]
    impact_metric: str
    impact_cr: float
    confidence_low_cr: float
    confidence_high_cr: float


class MacroPulseDashboardResponse(BaseModel):
    tenant_id: UUID
    generated_at: datetime
    headline: str
    kpi_tiles: list[MacroPulseDashboardTile]
    live_alerts: list[MacroPulseDashboardAlert]
    sensitivity_matrix: list[MacroPulseSensitivityRow]


class MacroPulseAgentQueryRequest(BaseModel):
    text: str = Field(min_length=3)
    tenant_id: UUID | None = None
    region: Literal["India", "UAE", "Saudi Arabia"] | None = None


class MacroPulseAgentSource(BaseModel):
    name: str
    category: Literal["official", "market", "news", "model"]
    detail: str


class MacroPulseAgentQueryResponse(BaseModel):
    query_type: Literal["interest_rate", "fx", "commodity", "combined", "overview"]
    impact: str
    confidence: float = Field(ge=0, le=100)
    publish_status: Literal["publish", "review", "hitl_queue"]
    recommended_action: str
    sources: list[MacroPulseAgentSource]
    regional_context: str
    scenario_output: dict
    analytics: dict
