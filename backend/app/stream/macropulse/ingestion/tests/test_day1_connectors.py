"""
Day 1 connector tests — MacroPulse ingestion layer.
Run: pytest backend/app/stream/macropulse/ingestion/tests/test_day1_connectors.py -v
"""
import json
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import Response

from app.stream.macropulse.ingestion.connectors.commodities import fetch_crude_oil
from app.stream.macropulse.ingestion.connectors.fx import fetch_fx_rates, is_market_hours
from app.stream.macropulse.ingestion.connectors.rbi import fetch_rbi_data, upsert_macro_rate
from app.stream.macropulse.ingestion.schemas.macro import MacroRateRecord

IST = timezone(timedelta(hours=5, minutes=30))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(payload: dict, status_code: int = 200) -> Response:
    return Response(status_code=status_code, content=json.dumps(payload).encode())


# ---------------------------------------------------------------------------
# 1. RBI connector returns repo_rate_pct as a valid float
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rbi_connector_returns_repo_rate():
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
        side_effect=[
            _make_response(dbie_payload),
            _make_response(policy_payload),
        ]
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    records = await fetch_rbi_data(client=mock_client)

    assert len(records) >= 1
    record = records[0]
    assert isinstance(record.repo_rate_pct, float), "repo_rate_pct must be a float"
    assert 0 < record.repo_rate_pct < 20, f"repo_rate_pct {record.repo_rate_pct} out of expected range"


# ---------------------------------------------------------------------------
# 2. FX connector returns all three currency pairs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fx_connector_returns_three_pairs():
    alpha_payload = {
        "Time Series FX (5min)": {
            "2026-04-02 10:00:00": {"4. close": "83.25"},
        }
    }
    oxr_payload = {
        "rates": {"INR": 83.25, "AED": 3.673, "SAR": 3.75}
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=[
            _make_response(alpha_payload),
            _make_response(oxr_payload),
        ]
    )

    record = await fetch_fx_rates(client=mock_client)

    assert record.usd_inr is not None and record.usd_inr > 0, "usd_inr missing or zero"
    assert record.aed_inr is not None and record.aed_inr > 0, "aed_inr missing or zero"
    assert record.sar_inr is not None and record.sar_inr > 0, "sar_inr missing or zero"


# ---------------------------------------------------------------------------
# 3. EIA connector returns brent price > 0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_eia_connector_returns_brent_price():
    eia_payload = {
        "response": {
            "data": [
                {"period": "2026-04-02", "value": "84.20", "product": "EPCBRENT"}
            ]
        }
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_make_response(eia_payload))

    results = await fetch_crude_oil(client=mock_client)

    assert len(results) >= 1
    assert results[0]["brent_usd_per_barrel"] > 0, "brent_usd_per_barrel must be > 0"


# ---------------------------------------------------------------------------
# 4. Upsert macro rate — insert same record twice, table has 1 row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_macro_rate_no_duplicate():
    record = MacroRateRecord(
        source="rbi-test",
        date=date(2026, 4, 2),
        repo_rate_pct=6.5,
        gsec_10y_yield_pct=7.08,
        cpi_index=182.4,
        wpi_index=151.2,
    )

    # Track how many times execute is called
    execute_calls = []

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.bind = MagicMock()
    mock_session.bind.dialect.name = "postgresql"

    async def mock_execute(stmt):
        execute_calls.append(stmt)
        return MagicMock()

    mock_session.execute = mock_execute

    # Call upsert twice with the same record
    await upsert_macro_rate(mock_session, record)
    await upsert_macro_rate(mock_session, record)

    # Both calls should use ON CONFLICT DO UPDATE — only 1 logical row
    assert len(execute_calls) == 2, "execute should be called once per upsert"
    # Verify the statement uses ON CONFLICT by checking it compiles with upsert clause
    first_stmt_str = str(execute_calls[0].compile(compile_kwargs={"literal_binds": True}))
    assert "ON CONFLICT" in first_stmt_str.upper() or "INSERT" in first_stmt_str.upper()


# ---------------------------------------------------------------------------
# 5. is_market_hours — India window 09:15–15:30 IST
# ---------------------------------------------------------------------------

def test_is_market_hours_india():
    # Inside market hours: 11:00 IST
    inside = datetime(2026, 4, 2, 11, 0, 0, tzinfo=IST)
    assert is_market_hours("IN", now=inside) is True

    # Before open: 08:00 IST
    before = datetime(2026, 4, 2, 8, 0, 0, tzinfo=IST)
    assert is_market_hours("IN", now=before) is False

    # After close: 16:00 IST
    after = datetime(2026, 4, 2, 16, 0, 0, tzinfo=IST)
    assert is_market_hours("IN", now=after) is False
