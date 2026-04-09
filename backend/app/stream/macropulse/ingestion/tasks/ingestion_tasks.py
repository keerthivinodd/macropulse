"""
Day 2 — Celery beat scheduler + ingestion tasks with DLQ support.
"""
import asyncio
import json
import os
from datetime import datetime, timezone

import redis as redis_lib
from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DLQ_KEY = "macropulse:dlq"

app = Celery("macropulse", broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_acks_late=True,
    beat_schedule={
        "fetch_fx_task": {
            "task": "app.stream.macropulse.ingestion.tasks.ingestion_tasks.fetch_fx_task",
            "schedule": crontab(minute="*/5"),
        },
        "fetch_macro_rates_task": {
            "task": "app.stream.macropulse.ingestion.tasks.ingestion_tasks.fetch_macro_rates_task",
            "schedule": crontab(minute=0),
        },
        "fetch_commodities_task": {
            "task": "app.stream.macropulse.ingestion.tasks.ingestion_tasks.fetch_commodities_task",
            "schedule": crontab(hour=1, minute=30),  # 07:00 IST = 01:30 UTC
        },
        "fetch_news_task": {
            "task": "app.stream.macropulse.ingestion.tasks.ingestion_tasks.fetch_news_task",
            "schedule": crontab(minute=0),
        },
        "embed_news_task": {
            "task": "app.stream.macropulse.ingestion.tasks.ingestion_tasks.embed_news_task",
            "schedule": crontab(minute=0, hour="*/2"),
        },
        # Day 3 — GCC central banks (daily 08:00 IST = 02:30 UTC)
        "fetch_sama_task": {
            "task": "app.stream.macropulse.ingestion.tasks.ingestion_tasks.fetch_sama_task",
            "schedule": crontab(hour=2, minute=30),
        },
        "fetch_cbuae_task": {
            "task": "app.stream.macropulse.ingestion.tasks.ingestion_tasks.fetch_cbuae_task",
            "schedule": crontab(hour=2, minute=30),
        },
        "fetch_regional_stats_task": {
            "task": "app.stream.macropulse.ingestion.tasks.ingestion_tasks.fetch_regional_stats_task",
            "schedule": crontab(hour=3, minute=0),
        },
        # Day 5 — Monday CFO Brief (07:00 IST = 01:30 UTC, Mondays only)
        "cfo_brief_weekly": {
            "task": "app.stream.macropulse.ingestion.tasks.ingestion_tasks.cfo_brief_weekly_task",
            "schedule": crontab(hour=1, minute=30, day_of_week="monday"),
        },
    },
)


# ---------------------------------------------------------------------------
# DLQ helpers
# ---------------------------------------------------------------------------

def _push_to_dlq(task_name: str, error: str) -> None:
    """Push failed task info to Redis dead-letter queue."""
    try:
        r = redis_lib.from_url(REDIS_URL)
        record = json.dumps({
            "task": task_name,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        r.rpush(DLQ_KEY, record)
    except Exception as e:
        logger.error("Failed to push to DLQ: %s", e)


def get_dlq_failures() -> list[dict]:
    """Return all failed task records from the Redis DLQ."""
    r = redis_lib.from_url(REDIS_URL)
    raw = r.lrange(DLQ_KEY, 0, -1)
    return [json.loads(item) for item in raw]


def _serialize_alert(alert) -> dict:
    return {
        "id": str(alert.id),
        "tenant_id": alert.tenant_id,
        "title": alert.title,
        "body": alert.body,
        "tier": alert.tier,
        "source_citation": alert.source_citation,
        "confidence_score": alert.confidence_score,
        "financial_impact_cr": alert.financial_impact_cr,
        "macro_variable": alert.macro_variable,
    }


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_fx_task(self) -> dict:
    from app.stream.macropulse.ingestion.connectors.fx import (
        fetch_fx_rates,
        is_market_hours,
    )
    from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
    from app.stream.macropulse.ingestion.models.fx_rates import FxRate

    try:
        if not is_market_hours("IN") and not is_market_hours("GCC"):
            return {"skipped": "outside market hours"}

        record = asyncio.run(fetch_fx_rates())

        async def _upsert():
            async with AsyncSessionLocal() as session:
                row = FxRate(
                    timestamp=record.timestamp,
                    usd_inr=record.usd_inr,
                    aed_inr=record.aed_inr,
                    sar_inr=record.sar_inr,
                    source=record.source,
                    region=record.region,
                )
                session.add(row)
                await session.commit()

        asyncio.run(_upsert())
        return record.model_dump(mode="json")
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _push_to_dlq("fetch_fx_task", str(exc))
            raise


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_macro_rates_task(self) -> list[dict]:
    from app.stream.macropulse.ingestion.connectors.rbi import (
        fetch_rbi_data,
        upsert_macro_rate,
    )
    from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal

    try:
        records = asyncio.run(fetch_rbi_data())

        async def _upsert_all():
            async with AsyncSessionLocal() as session:
                for rec in records:
                    await upsert_macro_rate(session, rec)

        asyncio.run(_upsert_all())
        return [r.model_dump(mode="json") for r in records]
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _push_to_dlq("fetch_macro_rates_task", str(exc))
            raise


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_commodities_task(self) -> dict:
    from app.stream.macropulse.ingestion.connectors.commodities import (
        fetch_crude_oil,
        fetch_mospi_wpi,
    )
    from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
    from app.stream.macropulse.ingestion.models.commodity_prices import CommodityPrice

    try:
        crude_rows, wpi_row = asyncio.run(asyncio.gather(
            fetch_crude_oil(), fetch_mospi_wpi()
        ))

        async def _upsert():
            async with AsyncSessionLocal() as session:
                for row in crude_rows:
                    session.add(CommodityPrice(
                        date=row["date"],
                        commodity="brent_crude",
                        price_value=row["brent_usd_per_barrel"],
                        unit="USD/barrel",
                        currency="USD",
                        region="GLOBAL",
                        source="EIA",
                    ))
                session.add(CommodityPrice(
                    date=wpi_row["date"],
                    commodity="wpi_index",
                    price_value=wpi_row["wpi_index"],
                    unit="index",
                    currency="INR",
                    region="IN",
                    source=wpi_row["source"],
                ))
                await session.commit()

        asyncio.run(_upsert())
        return {"crude": crude_rows, "wpi": wpi_row}
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _push_to_dlq("fetch_commodities_task", str(exc))
            raise


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_news_task(self) -> dict:
    from app.stream.macropulse.ingestion.connectors.news import fetch_all_news
    from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
    from app.stream.macropulse.ingestion.models.news_articles import NewsArticle

    try:
        articles = asyncio.run(fetch_all_news())

        async def _upsert():
            async with AsyncSessionLocal() as session:
                for a in articles:
                    existing = await session.execute(
                        __import__("sqlalchemy").select(NewsArticle).where(
                            NewsArticle.url == a["url"]
                        )
                    )
                    if existing.scalar_one_or_none() is None:
                        session.add(NewsArticle(**a))
                await session.commit()

        asyncio.run(_upsert())
        return {"ingested": len(articles)}
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _push_to_dlq("fetch_news_task", str(exc))
            raise


@app.task(bind=True, max_retries=3, default_retry_delay=120)
def embed_news_task(self) -> dict:
    from app.stream.macropulse.ingestion.etl.embedding_pipeline import run_embedding_batch

    try:
        result = asyncio.run(run_embedding_batch())
        return result
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _push_to_dlq("embed_news_task", str(exc))
            raise


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_sama_task(self) -> list[dict]:
    from app.stream.macropulse.ingestion.connectors.gcc_central_banks import fetch_sama_data
    from app.stream.macropulse.ingestion.connectors.rbi import upsert_macro_rate
    from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
    try:
        records = asyncio.run(fetch_sama_data())
        async def _upsert():
            async with AsyncSessionLocal() as session:
                for rec in records:
                    await upsert_macro_rate(session, rec)
        asyncio.run(_upsert())
        return [r.model_dump(mode="json") for r in records]
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _push_to_dlq("fetch_sama_task", str(exc))
            raise


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_cbuae_task(self) -> list[dict]:
    from app.stream.macropulse.ingestion.connectors.gcc_central_banks import fetch_cbuae_data
    from app.stream.macropulse.ingestion.connectors.rbi import upsert_macro_rate
    from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
    try:
        records = asyncio.run(fetch_cbuae_data())
        async def _upsert():
            async with AsyncSessionLocal() as session:
                for rec in records:
                    await upsert_macro_rate(session, rec)
        asyncio.run(_upsert())
        return [r.model_dump(mode="json") for r in records]
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _push_to_dlq("fetch_cbuae_task", str(exc))
            raise


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_regional_stats_task(self) -> dict:
    from app.stream.macropulse.ingestion.connectors.regional_stats import (
        fetch_fcsa,
        fetch_gastat,
        fetch_imf,
        fetch_world_bank,
    )
    from app.stream.macropulse.ingestion.connectors.rbi import upsert_macro_rate
    from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
    try:
        async def _fetch_all():
            return await asyncio.gather(
                fetch_gastat(), fetch_fcsa(), fetch_imf(), fetch_world_bank()
            )

        gastat_records, fcsa_records, imf_records, wb_records = asyncio.run(_fetch_all())
        all_records = gastat_records + fcsa_records + imf_records + wb_records
        async def _upsert():
            async with AsyncSessionLocal() as session:
                for rec in all_records:
                    await upsert_macro_rate(session, rec)
        asyncio.run(_upsert())
        return {
            "gastat": len(gastat_records),
            "fcsa": len(fcsa_records),
            "imf": len(imf_records),
            "world_bank": len(wb_records),
        }
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _push_to_dlq("fetch_regional_stats_task", str(exc))
            raise


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_p2_digest(self, tenant_id: str) -> dict:
    from sqlalchemy import select

    from app.stream.macropulse.ingestion.api.notification_tool import NotificationTool
    from app.stream.macropulse.ingestion.models.alerts import Alert
    from app.stream.macropulse.ingestion.models.tenant_profile import TenantProfileModel
    from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal

    try:
        async def _dispatch():
            async with AsyncSessionLocal() as session:
                profile = await session.get(TenantProfileModel, tenant_id)
                config = {}
                if profile and not profile.is_deleted:
                    config = profile.notification_config or profile.profile_data.get("notification_config", {})
                result = await session.execute(
                    select(Alert).where(
                        Alert.tenant_id == tenant_id,
                        Alert.tier == "P2",
                        Alert.status == "pending",
                    )
                )
                alerts = result.scalars().all()
                if not alerts:
                    return {"sent": 0}
                digest = Alert(
                    tenant_id=tenant_id,
                    alert_type="p2_digest",
                    tier="P2",
                    title=f"MacroPulse P2 digest ({len(alerts)} alerts)",
                    body="\n".join(f"- {a.title}" for a in alerts),
                    source_citation="MacroPulse Digest • 2026-04-03T00:00:00+05:30",
                    confidence_score=max(a.confidence_score for a in alerts),
                    financial_impact_cr=sum(a.financial_impact_cr or 0.0 for a in alerts) or None,
                    macro_variable="digest",
                    status="dispatched",
                )
                notifier = NotificationTool()
                result_payload = await notifier._dispatch_now(digest, config)
                for alert in alerts:
                    alert.status = "dispatched"
                    alert.dispatched_at = datetime.now(timezone.utc)
                await session.commit()
                return {"sent": len(alerts), "dispatch": result_payload}

        return asyncio.run(_dispatch())
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _push_to_dlq("dispatch_p2_digest", str(exc))
            raise


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_p3_digest(self, tenant_id: str) -> dict:
    from sqlalchemy import select

    from app.stream.macropulse.ingestion.api.notification_tool import NotificationTool
    from app.stream.macropulse.ingestion.models.alerts import Alert
    from app.stream.macropulse.ingestion.models.tenant_profile import TenantProfileModel
    from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal

    try:
        async def _dispatch():
            async with AsyncSessionLocal() as session:
                profile = await session.get(TenantProfileModel, tenant_id)
                config = {}
                if profile and not profile.is_deleted:
                    config = profile.notification_config or profile.profile_data.get("notification_config", {})
                result = await session.execute(
                    select(Alert).where(
                        Alert.tenant_id == tenant_id,
                        Alert.tier == "P3",
                        Alert.status == "pending",
                    )
                )
                alerts = result.scalars().all()
                if not alerts:
                    return {"sent": 0}
                digest = Alert(
                    tenant_id=tenant_id,
                    alert_type="p3_digest",
                    tier="P3",
                    title=f"MacroPulse hourly digest ({len(alerts)} alerts)",
                    body="\n".join(f"- {a.title}" for a in alerts),
                    source_citation="MacroPulse Digest • 2026-04-03T00:00:00+05:30",
                    confidence_score=max(a.confidence_score for a in alerts),
                    financial_impact_cr=sum(a.financial_impact_cr or 0.0 for a in alerts) or None,
                    macro_variable="digest",
                    status="dispatched",
                )
                notifier = NotificationTool()
                result_payload = await notifier._dispatch_now(digest, config)
                for alert in alerts:
                    alert.status = "dispatched"
                    alert.dispatched_at = datetime.now(timezone.utc)
                await session.commit()
                return {"sent": len(alerts), "dispatch": result_payload}

        return asyncio.run(_dispatch())
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _push_to_dlq("dispatch_p3_digest", str(exc))
            raise


# ---------------------------------------------------------------------------
# Day 5 — Monday CFO Brief pipeline (Pranisree)
# ---------------------------------------------------------------------------

@app.task(bind=True, max_retries=2, default_retry_delay=120)
def cfo_brief_weekly_task(self, tenant_id: str = "tenant-india-001") -> dict:
    """
    Monday 07:00 IST scheduled CFO Brief pipeline.
    Full flow: Pinecone retrieval → SQL KPIs → scenario sim → confidence
    → PDF/HTML export → Teams notification.
    """
    from app.stream.macropulse.cfo_brief_pipeline import run_cfo_brief_pipeline

    try:
        result = asyncio.run(run_cfo_brief_pipeline(
            tenant_id=tenant_id,
            upload_to_s3=True,
            notify=True,
            dry_run=False,
        ))
        logger.info(
            "CFO Brief pipeline completed: %d/%d steps, confidence=%.1f%%",
            result["steps_completed"], result["steps_total"], result["confidence_score"],
        )
        return result
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _push_to_dlq("cfo_brief_weekly_task", str(exc))
            raise
