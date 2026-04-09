from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc

from app.stream.macropulse.ingestion.api.middleware.residency import RegionResidencyMiddleware
from app.stream.macropulse.ingestion.db.session import Base, engine, AsyncSessionLocal
from app.stream.macropulse.ingestion.models import (  # noqa: F401
    alerts,
    commodity_prices,
    fx_rates,
    guardrail_violations,
    hitl_queue,
    macro_rates,
    news_articles,
    residency_violations,
    tenant_profile,
)
from app.stream.macropulse.ingestion.api.alert_engine import router as alerts_router
from app.stream.macropulse.ingestion.api.guardrails_runtime import router as guardrails_router
from app.stream.macropulse.ingestion.api.routes.dashboard import router as dashboard_router
from app.stream.macropulse.ingestion.api.routes.hitl import router as hitl_router
from app.stream.macropulse.ingestion.models.macro_rates import MacroRate
from app.stream.macropulse.ingestion.models.fx_rates import FxRate
from app.stream.macropulse.ingestion.models.commodity_prices import CommodityPrice
from app.stream.macropulse.ingestion.models.news_articles import NewsArticle
from app.stream.macropulse.ingestion.api.routes.tenant import router as tenant_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="MacroPulse API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RegionResidencyMiddleware)

app.include_router(tenant_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(hitl_router, prefix="/api")
app.include_router(guardrails_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "macropulse-api"}


# ---------------------------------------------------------------------------
# /api/macro-snapshot — live data from all connectors (no DB needed)
# ---------------------------------------------------------------------------

@app.get("/api/macro-snapshot")
async def macro_snapshot() -> dict[str, Any]:
    """
    Returns latest live data from all connectors in one call.
    Frontend can poll this every 5 minutes for a real-time dashboard.
    """
    import asyncio
    from app.stream.macropulse.ingestion.connectors.rbi import fetch_rbi_data
    from app.stream.macropulse.ingestion.connectors.fx import fetch_fx_rates
    from app.stream.macropulse.ingestion.connectors.commodities import fetch_crude_oil

    macro, fx, crude = await asyncio.gather(
        fetch_rbi_data(),
        fetch_fx_rates(),
        fetch_crude_oil(),
    )

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "macro_rates": macro[0].model_dump(mode="json") if macro else None,
        "fx_rates": fx.model_dump(mode="json"),
        "crude_oil": crude[0] if crude else None,
    }


# ---------------------------------------------------------------------------
# /api/macro-rates — historical records from DB
# ---------------------------------------------------------------------------

@app.get("/api/macro-rates")
async def get_macro_rates(limit: int = 30) -> list[dict]:
    """Returns last N macro rate records from the database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MacroRate).order_by(desc(MacroRate.date)).limit(limit)
        )
        rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "source": r.source,
            "date": r.date.isoformat(),
            "region": r.region,
            "repo_rate_pct": r.repo_rate_pct,
            "gsec_10y_yield_pct": r.gsec_10y_yield_pct,
            "cpi_index": r.cpi_index,
            "wpi_index": r.wpi_index,
            "saibor_3m_pct": r.saibor_3m_pct,
            "saibor_6m_pct": r.saibor_6m_pct,
            "eibor_1m_pct": r.eibor_1m_pct,
            "eibor_3m_pct": r.eibor_3m_pct,
            "confidence_tier": r.confidence_tier,
            "ingested_at": r.ingested_at.isoformat(),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# /api/fx-rates — latest FX records from DB
# ---------------------------------------------------------------------------

@app.get("/api/fx-rates")
async def get_fx_rates(limit: int = 50) -> list[dict]:
    """Returns last N FX rate records from the database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FxRate).order_by(desc(FxRate.timestamp)).limit(limit)
        )
        rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "usd_inr": r.usd_inr,
            "aed_inr": r.aed_inr,
            "sar_inr": r.sar_inr,
            "source": r.source,
            "region": r.region,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# /api/news — latest news articles from DB
# ---------------------------------------------------------------------------

@app.get("/api/news")
async def get_news(limit: int = 20, tag: str | None = None) -> list[dict]:
    """
    Returns latest news articles. Optionally filter by tag
    e.g. /api/news?tag=RBI or /api/news?tag=crude_oil
    """
    async with AsyncSessionLocal() as session:
        query = select(NewsArticle).order_by(desc(NewsArticle.ingested_at)).limit(limit)
        result = await session.execute(query)
        rows = result.scalars().all()

    articles = [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "url": r.url,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "source_name": r.source_name,
            "tags": r.tags or [],
            "embedded": r.embedded,
        }
        for r in rows
    ]

    if tag:
        articles = [a for a in articles if tag in (a["tags"] or [])]

    return articles


# ---------------------------------------------------------------------------
# /api/commodities — latest commodity prices from DB
# ---------------------------------------------------------------------------

@app.get("/api/commodities")
async def get_commodities(limit: int = 30) -> list[dict]:
    """Returns latest commodity price records from the database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CommodityPrice).order_by(desc(CommodityPrice.date)).limit(limit)
        )
        rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "date": r.date.isoformat(),
            "commodity": r.commodity,
            "price_value": r.price_value,
            "unit": r.unit,
            "currency": r.currency,
            "region": r.region,
            "source": r.source,
        }
        for r in rows
    ]
