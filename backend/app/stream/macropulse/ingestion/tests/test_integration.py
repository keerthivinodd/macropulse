from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import redis as redis_lib
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import delete, select

from app.stream.macropulse.ingestion.connectors.fx import fetch_fx_rates
from app.stream.macropulse.ingestion.connectors.rbi import fetch_rbi_data, upsert_macro_rate
from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
from app.stream.macropulse.ingestion.models.alerts import Alert
from app.stream.macropulse.ingestion.models.commodity_prices import CommodityPrice
from app.stream.macropulse.ingestion.models.fx_rates import FxRate
from app.stream.macropulse.ingestion.models.macro_rates import MacroRate
from app.stream.macropulse.ingestion.models.news_articles import NewsArticle
from app.stream.macropulse.ingestion.ops.api_main import app
from app.stream.macropulse.ingestion.tasks.ingestion_tasks import fetch_fx_task


def _tenant_payload(tenant_id: str, region: str = "IN") -> dict:
    currency = {"IN": "INR", "UAE": "AED", "SA": "SAR"}[region]
    return {
        "tenant_id": tenant_id,
        "company_name": f"{region} Test Co",
        "primary_region": region,
        "primary_currency": currency,
        "debt": {
            "total_loan_amount_cr": 100.0,
            "rate_type": "Floating",
            "current_effective_rate_pct": 9.5,
            "floating_proportion_pct": 65.0,
            "short_term_debt_cr": 30.0,
            "long_term_debt_cr": 70.0,
        },
        "fx": {
            "net_usd_exposure_m": 45.0,
            "net_aed_exposure_m": 10.0,
            "net_sar_exposure_m": 5.0,
            "hedge_ratio_pct": 65.0,
            "hedge_instrument": "Forward",
        },
        "cogs": {
            "total_cogs_cr": 100.0,
            "steel_pct": 20.0,
            "petroleum_pct": 30.0,
            "electronics_pct": 15.0,
            "freight_pct": 10.0,
            "other_pct": 25.0,
        },
        "portfolio": {
            "gsec_holdings_cr": 50.0,
            "modified_duration": 4.0,
        },
        "logistics": {
            "primary_routes": ["Mumbai-Dubai"],
            "monthly_shipment_value_cr": 10.0,
            "inventory_buffer_days": 30,
        },
        "notification_config": {
            "email": "cfo@example.com",
            "channels": ["email"],
        },
    }


async def _seed_dashboard_rows(region: str = "IN") -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(MacroRate).where(
                MacroRate.source == "RBI",
                MacroRate.region == region,
                MacroRate.date.in_([date(2026, 4, 1), date(2026, 4, 2)]),
            )
        )
        await session.execute(
            delete(FxRate).where(
                FxRate.source == "test",
                FxRate.region == region,
            )
        )
        await session.execute(
            delete(CommodityPrice).where(
                CommodityPrice.source == "EIA",
                CommodityPrice.commodity == "brent_crude",
                CommodityPrice.date.in_([date(2026, 3, 1), date(2026, 4, 1)]),
            )
        )
        session.add_all(
            [
                MacroRate(
                    source="RBI",
                    date=date(2026, 4, 1),
                    region=region,
                    repo_rate_pct=5.0,
                    gsec_10y_yield_pct=6.9,
                    wpi_index=150.0,
                ),
                MacroRate(
                    source="RBI",
                    date=date(2026, 4, 2),
                    region=region,
                    repo_rate_pct=5.25,
                    gsec_10y_yield_pct=7.0,
                    wpi_index=151.5,
                ),
                FxRate(
                    timestamp=datetime.now(UTC) - timedelta(days=7, minutes=5),
                    usd_inr=84.0,
                    aed_inr=22.8,
                    sar_inr=22.4,
                    source="test",
                    region=region,
                ),
                FxRate(
                    timestamp=datetime.now(UTC),
                    usd_inr=85.0,
                    aed_inr=23.0,
                    sar_inr=22.6,
                    source="test",
                    region=region,
                ),
                CommodityPrice(
                    date=date(2026, 3, 1),
                    commodity="brent_crude",
                    price_value=80.0,
                    unit="USD/barrel",
                    currency="USD",
                    region="GLOBAL",
                    source="EIA",
                ),
                CommodityPrice(
                    date=date(2026, 4, 1),
                    commodity="brent_crude",
                    price_value=88.0,
                    unit="USD/barrel",
                    currency="USD",
                    region="GLOBAL",
                    source="EIA",
                ),
            ]
        )
        await session.commit()


def _make_response(payload: dict, status_code: int = 200) -> Response:
    return Response(status_code=status_code, content=json.dumps(payload).encode())


@pytest.mark.asyncio
async def test_dashboard_returns_kpi_tiles():
    tenant_id = f"dash-{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tenant/profile", json=_tenant_payload(tenant_id))
        await _seed_dashboard_rows()
        response = await client.get(f"/api/macropulse/dashboard/{tenant_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["kpi_tiles"]["repo_rate_pct"] is not None
    assert body["kpi_tiles"]["usd_inr_rate"] > 0


@pytest.mark.asyncio
async def test_dashboard_cached_in_redis():
    tenant_id = f"cache-{uuid.uuid4().hex[:8]}"
    redis_client = redis_lib.from_url("redis://localhost:6379/0")
    redis_client.delete(f"dashboard:{tenant_id}")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tenant/profile", json=_tenant_payload(tenant_id))
        await _seed_dashboard_rows()
        await client.get(f"/api/macropulse/dashboard/{tenant_id}")
        await client.get(f"/api/macropulse/dashboard/{tenant_id}")
    assert redis_client.exists(f"dashboard:{tenant_id}") == 1
    assert redis_client.ttl(f"dashboard:{tenant_id}") <= 60


@pytest.mark.asyncio
async def test_rbi_connector_populates_macro_rates():
    dbie_payload = {
        "data": [
            {
                "date": "2026-04-02T00:00:00+05:30",
                "repo_rate": 6.5,
                "gsec_10y_yield": 7.08,
                "cpi_index": 182.4,
                "wpi_index": 151.2,
            }
        ]
    }
    policy_payload = {"data": {"repo_rate": 6.5, "date": "2026-04-02T00:00:00+05:30"}}
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=[_make_response(dbie_payload), _make_response(policy_payload)]
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    rows = await fetch_rbi_data(client=mock_client)
    async with AsyncSessionLocal() as session:
        for row in rows:
            await upsert_macro_rate(session, row)
        result = await session.execute(select(MacroRate).where(MacroRate.source == "RBI"))
        record = result.scalars().first()
    assert record is not None


@pytest.mark.asyncio
async def test_fx_connector_all_three_pairs():
    record = await fetch_fx_rates()
    assert record.usd_inr > 0
    assert record.aed_inr > 0
    assert record.sar_inr > 0


@pytest.mark.asyncio
async def test_celery_task_stores_data(monkeypatch):
    sample = SimpleNamespace(
        timestamp=datetime.now(UTC),
        usd_inr=84.0,
        aed_inr=22.8,
        sar_inr=22.4,
        source="test",
        region="IN",
        model_dump=lambda mode="json": {"usd_inr": 84.0},
    )
    monkeypatch.setattr(
        "app.stream.macropulse.ingestion.connectors.fx.fetch_fx_rates",
        AsyncMock(return_value=sample),
    )
    fetch_fx_task.apply()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(FxRate).where(FxRate.source == "test").order_by(FxRate.id.desc()))
        row = result.scalars().first()
    assert row is not None


@pytest.mark.asyncio
async def test_sensitivity_matrix_endpoint():
    tenant_id = f"sens-{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tenant/profile", json=_tenant_payload(tenant_id))
        response = await client.get(f"/api/tenant/profile/{tenant_id}/sensitivity")
    assert response.status_code == 200
    impact = response.json()["data"]["REPO_RATE"]["impact_cr"]
    assert impact == pytest.approx(0.1625, abs=0.001)


@pytest.mark.asyncio
async def test_p1_alert_classified_correctly(monkeypatch):
    monkeypatch.setattr(
        "app.stream.macropulse.ingestion.api.alert_engine.NotificationTool.dispatch",
        AsyncMock(return_value={"dispatch_latency_ms": 10}),
    )
    tenant_id = f"alert-{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tenant/profile", json=_tenant_payload(tenant_id))
        response = await client.post(
            "/api/alerts/classify",
            json={
                "tenant_id": tenant_id,
                "agent_output": {
                    "macro_variable": "repo_rate",
                    "confidence_score": 0.92,
                    "title": "CEO John Smith said repo moved",
                    "body": "CEO John Smith said repo moved",
                    "source_citation": "RBI Bulletin ? 2026-04-01T09:30:00+05:30",
                },
            },
        )
    assert response.status_code == 200
    assert response.json()["tier"] == "P1"
    assert response.json()["status"] in {"pending", "dispatched"}


@pytest.mark.asyncio
async def test_low_confidence_routes_to_hitl(monkeypatch):
    monkeypatch.setattr(
        "app.stream.macropulse.ingestion.api.alert_engine.NotificationTool.dispatch",
        AsyncMock(return_value={"dispatch_latency_ms": 10}),
    )
    tenant_id = f"hitl-{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tenant/profile", json=_tenant_payload(tenant_id))
        response = await client.post(
            "/api/alerts/classify",
            json={
                "tenant_id": tenant_id,
                "agent_output": {
                    "macro_variable": "fx_usd_inr",
                    "confidence_score": 0.78,
                    "title": "FX moved",
                    "body": "FX moved",
                    "source_citation": "RBI Bulletin ? 2026-04-01T09:30:00+05:30",
                },
            },
        )
        pending = await client.get("/api/hitl/pending")
    assert response.status_code == 200
    assert response.json()["status"] == "hitl_queued"
    assert any(item["tenant_id"] == tenant_id for item in pending.json())


@pytest.mark.asyncio
async def test_hitl_approve_changes_status(monkeypatch):
    monkeypatch.setattr(
        "app.stream.macropulse.ingestion.api.alert_engine.NotificationTool.dispatch",
        AsyncMock(return_value={"dispatch_latency_ms": 10}),
    )
    monkeypatch.setattr(
        "app.stream.macropulse.ingestion.api.routes.hitl.NotificationTool.dispatch",
        AsyncMock(return_value={"dispatch_latency_ms": 10}),
    )
    tenant_id = f"approve-{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tenant/profile", json=_tenant_payload(tenant_id))
        response = await client.post(
            "/api/alerts/classify",
            json={
                "tenant_id": tenant_id,
                "agent_output": {
                    "macro_variable": "fx_usd_inr",
                    "confidence_score": 0.78,
                    "title": "FX moved",
                    "body": "FX moved",
                    "source_citation": "RBI Bulletin ? 2026-04-01T09:30:00+05:30",
                },
            },
        )
        alert_id = response.json()["id"]
        approve = await client.post(
            f"/api/hitl/{alert_id}/approve",
            json={"reviewer": "analyst", "notes": "approved"},
        )
        alert = await client.get(f"/api/alerts/{alert_id}")
    assert approve.status_code == 200
    assert alert.json()["status"] == "dispatched"


@pytest.mark.asyncio
async def test_pii_redaction_in_stored_alert(monkeypatch):
    monkeypatch.setattr(
        "app.stream.macropulse.ingestion.api.alert_engine.NotificationTool.dispatch",
        AsyncMock(return_value={"dispatch_latency_ms": 10}),
    )
    tenant_id = f"pii-{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tenant/profile", json=_tenant_payload(tenant_id))
        response = await client.post(
            "/api/alerts/classify",
            json={
                "tenant_id": tenant_id,
                "agent_output": {
                    "macro_variable": "repo_rate",
                    "confidence_score": 0.92,
                    "title": "CEO John Smith said repo moved",
                    "body": "CEO John Smith said repo moved",
                    "source_citation": "RBI Bulletin ? 2026-04-01T09:30:00+05:30",
                },
            },
        )
        alert = await client.get(f"/api/alerts/{response.json()['id']}")
    assert "[PERSON REDACTED]" in alert.json()["body"]


@pytest.mark.asyncio
async def test_guardrail_blocks_no_source():
    tenant_id = f"guard-{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tenant/profile", json=_tenant_payload(tenant_id))
        response = await client.post(
            "/api/alerts/classify",
            json={
                "tenant_id": tenant_id,
                "agent_output": {
                    "macro_variable": "repo_rate",
                    "confidence_score": 0.92,
                    "title": "No source",
                    "body": "No source",
                    "source_citation": "",
                },
            },
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_residency_india_routes_correctly(monkeypatch):
    captured = []
    original = __import__("app.stream.macropulse.ingestion.api.middleware.residency", fromlist=["set_session_region"]).set_session_region

    def recorder(region: str):
        captured.append(region)
        return original(region)

    monkeypatch.setattr(
        "app.stream.macropulse.ingestion.api.middleware.residency.set_session_region",
        recorder,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tenant/profile", json=_tenant_payload(f"india-{uuid.uuid4().hex[:8]}", "IN"))
    assert "IN" in captured


@pytest.mark.asyncio
async def test_embedding_pipeline_end_to_end(monkeypatch):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(NewsArticle).where(NewsArticle.source_name == "integration-test"))
        session.add_all(
            [
                NewsArticle(title=f"Article {i}", description="Desc", url=f"https://example.com/{uuid.uuid4().hex}{i}", source_name="integration-test", tags=["RBI"], embedded=False)
                for i in range(3)
            ]
        )
        await session.commit()

    mock_embedding = SimpleNamespace(embedding=[0.1] * 10)
    mock_openai = SimpleNamespace(
        embeddings=SimpleNamespace(
            create=lambda model, input: SimpleNamespace(data=[mock_embedding for _ in input])
        )
    )
    upserts = []
    mock_index = SimpleNamespace(upsert=lambda vectors: upserts.append(vectors))
    monkeypatch.setattr(
        "app.stream.macropulse.ingestion.etl.embedding_pipeline._get_openai_client",
        lambda: mock_openai,
    )
    monkeypatch.setattr(
        "app.stream.macropulse.ingestion.etl.embedding_pipeline._get_pinecone_index",
        lambda: mock_index,
    )

    from app.stream.macropulse.ingestion.etl.embedding_pipeline import run_embedding_batch

    result = await run_embedding_batch()
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(select(NewsArticle).where(NewsArticle.source_name == "integration-test"))
        ).scalars().all()
    assert result["embedded"] == 3
    assert all(row.embedded for row in rows)
    assert len(upserts) == 1


@pytest.mark.asyncio
async def test_p1_dispatch_latency_under_60s():
    from app.stream.macropulse.ingestion.api.notification_tool import NotificationTool

    alert = Alert(
        tenant_id="latency",
        alert_type="macro_signal",
        tier="P1",
        title="Immediate",
        body="Immediate",
        source_citation="RBI Bulletin ? 2026-04-01T09:30:00+05:30",
        confidence_score=0.9,
        financial_impact_cr=1.0,
        macro_variable="repo_rate",
        status="pending",
    )
    notifier = NotificationTool()
    notifier._send_email = AsyncMock(return_value={"channel": "email"})
    result = await notifier.dispatch(alert, {"channels": ["email"], "email": "cfo@example.com"})
    assert result["dispatch_latency_ms"] < 60_000


@pytest.mark.asyncio
async def test_sensitivity_recalculates_after_profile_update():
    tenant_id = f"recalc-{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = _tenant_payload(tenant_id)
        await client.post("/api/tenant/profile", json=payload)
        before = await client.get(f"/api/tenant/profile/{tenant_id}/sensitivity")
        payload["debt"]["floating_proportion_pct"] = 90.0
        await client.put(f"/api/tenant/profile/{tenant_id}", json=payload)
        after = await client.get(f"/api/tenant/profile/{tenant_id}/sensitivity")
    assert before.json()["data"]["REPO_RATE"]["impact_cr"] != after.json()["data"]["REPO_RATE"]["impact_cr"]
