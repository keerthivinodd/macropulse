from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.main import app
from app.stream.macropulse.router import get_macropulse_realtime
from app.stream.macropulse.schemas import (
    MacroPulseIndicator,
    MacroPulseRealtimeResponse,
    MacroPulseSourceStatus,
)


@pytest.mark.asyncio
async def test_macropulse_realtime_endpoint(client):
    async def override_snapshot():
        return MacroPulseRealtimeResponse(
            headline="Inflation remains firm while long-end rates stay elevated.",
            narrative="Official data sources are flowing into MacroPulse.",
            anomaly_confidence=93.4,
            market_confidence_score=8.1,
            global_sentiment_change=1.2,
            generated_at=datetime(2026, 3, 31, tzinfo=UTC),
            indicators=[
                MacroPulseIndicator(
                    key="eurusd",
                    symbol="EUR / USD",
                    label="ECB Reference Rate",
                    value="1.0811",
                    sub="Euro reference rate against the U.S. dollar",
                    change="+0.21%",
                    dir="up",
                    source="ECB",
                    as_of=datetime(2026, 3, 31, tzinfo=UTC),
                )
            ],
            sources=[
                MacroPulseSourceStatus(
                    name="European Central Bank FX Feed",
                    status="live",
                    latency="Daily",
                    coverage="EUR/USD reference rates",
                )
            ],
        )

    mocked = AsyncMock(side_effect=override_snapshot)
    app.dependency_overrides.clear()
    from app.stream.macropulse import router as macropulse_router_module
    original = macropulse_router_module.MacroPulseService.get_realtime_snapshot
    macropulse_router_module.MacroPulseService.get_realtime_snapshot = mocked
    try:
        response = await client.get("/api/v1/macropulse/realtime")
    finally:
        macropulse_router_module.MacroPulseService.get_realtime_snapshot = original

    assert response.status_code == 200
    body = response.json()
    assert body["headline"].startswith("Inflation remains firm")
    assert body["indicators"][0]["symbol"] == "EUR / USD"
