from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import redis as redis_lib
from fastapi import APIRouter, HTTPException
from sqlalchemy import desc, select

from app.stream.macropulse.ingestion.etl.sensitivity import (
    calculate_sensitivity_matrix,
    get_cached_sensitivity,
)
from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
from app.stream.macropulse.ingestion.models.alerts import Alert
from app.stream.macropulse.ingestion.models.commodity_prices import CommodityPrice
from app.stream.macropulse.ingestion.models.fx_rates import FxRate
from app.stream.macropulse.ingestion.models.macro_rates import MacroRate
from app.stream.macropulse.ingestion.models.news_articles import NewsArticle
from app.stream.macropulse.ingestion.models.tenant_profile import TenantProfileModel
from app.stream.macropulse.ingestion.schemas.dashboard import (
    AlertSummary,
    DataFreshness,
    KPITiles,
    MacroPulseDashboard,
)
from app.stream.macropulse.ingestion.schemas.tenant_profile import TenantProfile

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DASHBOARD_TTL = 60

router = APIRouter(prefix="/macropulse", tags=["dashboard"])


def _redis():
    return redis_lib.from_url(REDIS_URL)


async def _load_profile(tenant_id: str) -> TenantProfile:
    async with AsyncSessionLocal() as session:
        row = await session.get(TenantProfileModel, tenant_id)
        if not row or row.is_deleted:
            raise HTTPException(status_code=404, detail="Tenant profile not found")
        return TenantProfile(**row.profile_data)


async def _build_sensitivity(profile: TenantProfile) -> dict:
    cached = get_cached_sensitivity(profile.tenant_id)
    if cached:
        return cached

    async with AsyncSessionLocal() as session:
        fx_result = await session.execute(
            select(FxRate).order_by(desc(FxRate.timestamp)).limit(1)
        )
        fx_row = fx_result.scalars().first()
        commodity_result = await session.execute(
            select(CommodityPrice)
            .where(CommodityPrice.commodity == "brent_crude")
            .order_by(desc(CommodityPrice.date))
            .limit(1)
        )
        brent_row = commodity_result.scalars().first()

    fx_rates = {
        "usd_inr": fx_row.usd_inr if fx_row else 84.0,
        "aed_inr": fx_row.aed_inr if fx_row else 22.87,
        "sar_inr": fx_row.sar_inr if fx_row else 22.40,
    }
    brent = brent_row.price_value if brent_row else 80.0
    return calculate_sensitivity_matrix(profile, fx_rates, brent)


@router.get(
    "/dashboard/{tenant_id}",
    response_model=MacroPulseDashboard,
    summary="Get MacroPulse dashboard snapshot",
    description="Returns KPI tiles, live alerts, sensitivity matrix, and data freshness for a tenant.",
)
async def get_dashboard(tenant_id: str) -> MacroPulseDashboard:
    try:
        cached = _redis().get(f"dashboard:{tenant_id}")
        if cached:
            return MacroPulseDashboard(**json.loads(cached))
    except Exception:
        pass

    profile = await _load_profile(tenant_id)
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        macro_result = await session.execute(
            select(MacroRate)
            .where(MacroRate.region == profile.primary_region)
            .order_by(desc(MacroRate.date))
            .limit(2)
        )
        macro_rows = macro_result.scalars().all()

        latest_fx_result = await session.execute(
            select(FxRate).order_by(desc(FxRate.timestamp)).limit(1)
        )
        latest_fx = latest_fx_result.scalars().first()
        prior_fx_result = await session.execute(
            select(FxRate)
            .where(FxRate.timestamp <= now - timedelta(days=7))
            .order_by(desc(FxRate.timestamp))
            .limit(1)
        )
        prior_fx = prior_fx_result.scalars().first()

        brent_result = await session.execute(
            select(CommodityPrice)
            .where(CommodityPrice.commodity == "brent_crude")
            .order_by(desc(CommodityPrice.date))
            .limit(2)
        )
        brent_rows = brent_result.scalars().all()

        alert_result = await session.execute(
            select(Alert)
            .where(
                Alert.tenant_id == tenant_id,
                Alert.status.in_(["pending", "dispatched"]),
            )
            .order_by(Alert.tier.asc(), Alert.confidence_score.desc())
            .limit(5)
        )
        alerts = alert_result.scalars().all()

        news_result = await session.execute(
            select(NewsArticle).order_by(desc(NewsArticle.ingested_at)).limit(1)
        )
        latest_news = news_result.scalars().first()

    current_macro = macro_rows[0] if macro_rows else None
    prior_macro = macro_rows[1] if len(macro_rows) > 1 else None
    repo_rate_change_bps = None
    wpi_mom_change_pct = None
    if current_macro and prior_macro and current_macro.repo_rate_pct is not None and prior_macro.repo_rate_pct is not None:
        repo_rate_change_bps = round((current_macro.repo_rate_pct - prior_macro.repo_rate_pct) * 100, 2)
    if current_macro and prior_macro and current_macro.wpi_index and prior_macro.wpi_index:
        wpi_mom_change_pct = round(((current_macro.wpi_index - prior_macro.wpi_index) / prior_macro.wpi_index) * 100, 2)

    usd_change_pct = None
    if latest_fx and prior_fx and prior_fx.usd_inr:
        usd_change_pct = round(((latest_fx.usd_inr - prior_fx.usd_inr) / prior_fx.usd_inr) * 100, 2)

    latest_brent = brent_rows[0] if brent_rows else None
    prior_brent = brent_rows[1] if len(brent_rows) > 1 else None
    brent_change_pct = None
    if latest_brent and prior_brent and prior_brent.price_value:
        brent_change_pct = round(((latest_brent.price_value - prior_brent.price_value) / prior_brent.price_value) * 100, 2)

    recent_cutoff = now - timedelta(hours=24)
    repo_rate_alert = any(
        alert.macro_variable == "repo_rate" and alert.tier in {"P1", "P2"} and alert.created_at >= recent_cutoff
        for alert in alerts
    )
    fx_alert = any(
        alert.macro_variable == "fx_usd_inr" and alert.tier in {"P1", "P2"} and alert.created_at >= recent_cutoff
        for alert in alerts
    )
    inflation_alert = any(
        alert.macro_variable == "cpi_wpi" and alert.tier in {"P1", "P2"} and alert.created_at >= recent_cutoff
        for alert in alerts
    )
    oil_alert = any(
        alert.macro_variable in {"crude_oil", "commodity"} and alert.created_at >= recent_cutoff
        for alert in alerts
    )

    sensitivity = await _build_sensitivity(profile)

    dashboard = MacroPulseDashboard(
        tenant_id=tenant_id,
        primary_currency=profile.primary_currency,
        generated_at=now,
        kpi_tiles=KPITiles(
            repo_rate_pct=current_macro.repo_rate_pct if current_macro else None,
            repo_rate_change_bps=repo_rate_change_bps,
            repo_rate_alert=repo_rate_alert,
            usd_inr_rate=latest_fx.usd_inr if latest_fx else None,
            usd_inr_7d_change_pct=usd_change_pct,
            fx_alert=fx_alert,
            wpi_index=current_macro.wpi_index if current_macro else None,
            wpi_mom_change_pct=wpi_mom_change_pct,
            inflation_alert=inflation_alert,
            brent_usd=latest_brent.price_value if latest_brent else None,
            brent_mom_change_pct=brent_change_pct,
            oil_alert=oil_alert,
        ),
        live_alerts=[
            AlertSummary(
                id=str(alert.id),
                title=alert.title,
                tier=alert.tier,
                status=alert.status,
                macro_variable=alert.macro_variable,
                confidence_score=alert.confidence_score,
                created_at=alert.created_at,
            )
            for alert in alerts
        ],
        sensitivity_matrix=sensitivity,
        data_freshness=DataFreshness(
            rbi=current_macro.ingested_at if current_macro else None,
            fx_rates=latest_fx.ingested_at if latest_fx else None,
            commodities=latest_brent.ingested_at if latest_brent else None,
            news=latest_news.ingested_at if latest_news else None,
        ),
    )

    try:
        _redis().setex(
            f"dashboard:{tenant_id}",
            DASHBOARD_TTL,
            dashboard.model_dump_json(),
        )
    except Exception:
        pass

    return dashboard
