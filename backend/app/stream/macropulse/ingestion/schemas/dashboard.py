from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AlertSummary(BaseModel):
    id: str
    title: str
    tier: str
    status: str
    macro_variable: str
    confidence_score: float
    created_at: datetime


class KPITiles(BaseModel):
    repo_rate_pct: float | None = None
    repo_rate_change_bps: float | None = None
    repo_rate_alert: bool = False
    usd_inr_rate: float | None = None
    usd_inr_7d_change_pct: float | None = None
    fx_alert: bool = False
    wpi_index: float | None = None
    wpi_mom_change_pct: float | None = None
    inflation_alert: bool = False
    brent_usd: float | None = None
    brent_mom_change_pct: float | None = None
    oil_alert: bool = False


class DataFreshness(BaseModel):
    rbi: datetime | None = None
    fx_rates: datetime | None = None
    commodities: datetime | None = None
    news: datetime | None = None


class MacroPulseDashboard(BaseModel):
    tenant_id: str
    primary_currency: str
    generated_at: datetime
    kpi_tiles: KPITiles
    live_alerts: list[AlertSummary] = Field(default_factory=list)
    sensitivity_matrix: dict = Field(default_factory=dict)
    data_freshness: DataFreshness
