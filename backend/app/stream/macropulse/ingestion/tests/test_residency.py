from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.stream.macropulse.ingestion.api.middleware.residency import get_engine_url
from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
from app.stream.macropulse.ingestion.models.residency_violations import ResidencyViolation
from app.stream.macropulse.ingestion.ops.api_main import app


def _tenant_payload(region: str) -> dict:
    tenant_id = f"res-{region.lower()}-{uuid.uuid4().hex[:8]}"
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


def test_india_tenant_routes_to_india_db(monkeypatch):
    monkeypatch.setattr(
        "app.stream.macropulse.ingestion.db.session._ENGINE_URLS",
        {
            "DEFAULT": "postgresql+asyncpg://postgres:test@localhost/macropulse_test",
            "IN": "postgresql+asyncpg://postgres:test@localhost/india-region",
            "UAE": "postgresql+asyncpg://postgres:test@localhost/uae-region",
            "SA": "postgresql+asyncpg://postgres:test@localhost/uae-region",
        },
        raising=False,
    )
    assert "india-region" in get_engine_url("IN")


def test_gcc_tenant_routes_to_gcc_db(monkeypatch):
    monkeypatch.setattr(
        "app.stream.macropulse.ingestion.db.session._ENGINE_URLS",
        {
            "DEFAULT": "postgresql+asyncpg://postgres:test@localhost/macropulse_test",
            "IN": "postgresql+asyncpg://postgres:test@localhost/india-region",
            "UAE": "postgresql+asyncpg://postgres:test@localhost/uae-region",
            "SA": "postgresql+asyncpg://postgres:test@localhost/uae-region",
        },
        raising=False,
    )
    assert "uae-region" in get_engine_url("UAE")


@pytest.mark.asyncio
async def test_cross_region_write_returns_403():
    payload = _tenant_payload("IN")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/tenant/profile",
            json=payload,
            headers={"x-write-region": "UAE"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_violation_logged_to_table():
    payload = _tenant_payload("IN")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/tenant/profile",
            json=payload,
            headers={"x-write-region": "UAE"},
        )
        assert response.status_code == 403

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ResidencyViolation).where(ResidencyViolation.tenant_id == payload["tenant_id"])
        )
        row = result.scalars().first()
    assert row is not None
    assert row.correct_region == "IN"


@pytest.mark.asyncio
async def test_read_ops_bypass_residency():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health", headers={"x-write-region": "UAE"})
    assert response.status_code == 200
