from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.stream.macropulse.ingestion.connectors.commodities import fetch_crude_oil
from app.stream.macropulse.ingestion.connectors.fx import fetch_fx_rates, is_market_hours
from app.stream.macropulse.ingestion.connectors.rbi import fetch_rbi_data, upsert_macro_rate
from app.stream.macropulse.ingestion.db.session import Base
from app.stream.macropulse.ingestion.models.macro_rates import MacroRate


def transport_for(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_rbi_connector_returns_repo_rate():
    def handler(request: httpx.Request) -> httpx.Response:
        if "dbie.rbi.org.in" in str(request.url):
            return httpx.Response(
                200,
                json={"data": [{"date": "2026-04-01T09:00:00Z", "cpi_index": 182.4, "wpi_index": 151.2}]},
            )
        return httpx.Response(
            200,
            json={"data": {"repo_rate": 6.5, "gsec_10y_yield": 7.12, "date": "2026-04-01T10:00:00Z"}},
        )

    async with httpx.AsyncClient(transport=transport_for(handler)) as client:
        rows = await fetch_rbi_data(client)

    assert rows
    assert isinstance(rows[0].repo_rate_pct, float)
    assert 0 < rows[0].repo_rate_pct < 20


@pytest.mark.asyncio
async def test_fx_connector_returns_three_pairs():
    def handler(request: httpx.Request) -> httpx.Response:
        if "alphavantage.co" in str(request.url):
            return httpx.Response(
                200,
                json={"Time Series FX (5min)": {"2026-04-01 10:00:00": {"4. close": "83.2500"}}},
            )
        return httpx.Response(
            200,
            json={"rates": {"INR": 83.25, "AED": 3.6725, "SAR": 3.75}},
        )

    async with httpx.AsyncClient(transport=transport_for(handler)) as client:
        row = await fetch_fx_rates(client)

    assert row.usd_inr > 0
    assert row.aed_inr > 0
    assert row.sar_inr > 0


@pytest.mark.asyncio
async def test_eia_connector_returns_brent_price():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"response": {"data": [{"period": "2026-04-01", "value": 84.2, "wti_value": 80.1}]}},
        )

    async with httpx.AsyncClient(transport=transport_for(handler)) as client:
        rows = await fetch_crude_oil(client)

    assert rows[0]["brent_usd_per_barrel"] > 0


@pytest.mark.asyncio
async def test_upsert_macro_rate_no_duplicate():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    record = (await fetch_rbi_data(
        httpx.AsyncClient(
            transport=transport_for(
                lambda request: httpx.Response(
                    200,
                    json=(
                        {"data": [{"date": "2026-04-01T09:00:00Z", "cpi_index": 182.4, "wpi_index": 151.2}]}
                        if "dbie.rbi.org.in" in str(request.url)
                        else {"data": {"repo_rate": 6.5, "gsec_10y_yield": 7.12, "date": "2026-04-01T10:00:00Z"}}
                    ),
                )
            )
        )
    ))[0]

    async with session_factory() as session:
        await upsert_macro_rate(session, record)
        await upsert_macro_rate(session, record)
        count = await session.scalar(select(func.count()).select_from(MacroRate))

    await engine.dispose()
    assert count == 1


def test_is_market_hours_india():
    now = datetime(2026, 4, 1, 5, 0, tzinfo=UTC)
    assert is_market_hours("IN", now=now) is True
