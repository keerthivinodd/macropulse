"""
MacroPulse Redis Pub/Sub Event Publisher — Day 5 (Pranisree)

Publishes MacroPulse output events to Redis pub/sub channels for downstream consumers:
  - macro.currency_signal   → GeoRisk module
  - macro.slowdown_risk     → ChurnGuard module
  - macro.commodity_inflation → SLAMonitor module

Event schemas documented inline and in /docs.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Event Channels ───────────────────────────────────────────

class MacroPulseChannel(str, Enum):
    CURRENCY_SIGNAL = "macro.currency_signal"
    SLOWDOWN_RISK = "macro.slowdown_risk"
    COMMODITY_INFLATION = "macro.commodity_inflation"


# Channel → downstream consumer mapping
CHANNEL_CONSUMERS: dict[str, str] = {
    MacroPulseChannel.CURRENCY_SIGNAL: "GeoRisk",
    MacroPulseChannel.SLOWDOWN_RISK: "ChurnGuard",
    MacroPulseChannel.COMMODITY_INFLATION: "SLAMonitor",
}


# ── Event Schemas (Pydantic) ────────────────────────────────

class BaseEvent(BaseModel):
    """Base schema for all MacroPulse pub/sub events."""
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str
    channel: str
    tenant_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "macropulse"
    version: str = "1.0"


class CurrencySignalEvent(BaseEvent):
    """
    Published to: macro.currency_signal
    Consumer: GeoRisk module

    Fired when MacroPulse detects significant FX movement, central bank
    policy change, or currency risk signal.
    """
    event_type: str = "currency_signal"
    channel: str = MacroPulseChannel.CURRENCY_SIGNAL

    currency_pair: str = Field(..., description="e.g. USD/INR, AED/INR")
    signal_type: str = Field(..., description="depreciation | appreciation | volatility_spike | policy_change")
    magnitude_pct: float = Field(..., description="Percentage change or z-score")
    direction: str = Field(..., description="up | down | mixed")
    confidence: float = Field(..., ge=0, le=1, description="Signal confidence score")
    source_citation: str = Field(default="", description="Data source citation")
    recommended_action: str = Field(default="", description="Suggested hedging/action")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SlowdownRiskEvent(BaseEvent):
    """
    Published to: macro.slowdown_risk
    Consumer: ChurnGuard module

    Fired when macro indicators suggest economic slowdown risk that could
    impact customer retention and churn rates.
    """
    event_type: str = "slowdown_risk"
    channel: str = MacroPulseChannel.SLOWDOWN_RISK

    risk_level: str = Field(..., description="low | medium | high | critical")
    risk_score: float = Field(..., ge=0, le=100, description="Composite slowdown risk score 0-100")
    indicators: list[str] = Field(default_factory=list, description="Contributing macro indicators")
    gdp_growth_delta_pct: float = Field(default=0.0, description="GDP growth change vs prior quarter")
    inflation_trend: str = Field(default="stable", description="rising | falling | stable")
    interest_rate_direction: str = Field(default="hold", description="hike | cut | hold")
    affected_regions: list[str] = Field(default_factory=list, description="Regions with elevated risk")
    confidence: float = Field(..., ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommodityInflationEvent(BaseEvent):
    """
    Published to: macro.commodity_inflation
    Consumer: SLAMonitor module

    Fired when commodity price movements could impact cost structures,
    SLA pricing, and margin thresholds.
    """
    event_type: str = "commodity_inflation"
    channel: str = MacroPulseChannel.COMMODITY_INFLATION

    commodity: str = Field(..., description="e.g. brent_crude, gold, natural_gas, copper")
    price_change_pct: float = Field(..., description="Price change percentage (MoM)")
    current_price_usd: float = Field(default=0.0, description="Current price in USD")
    direction: str = Field(..., description="up | down")
    impact_on_cogs_pct: float = Field(default=0.0, description="Estimated COGS impact %")
    affected_cost_categories: list[str] = Field(default_factory=list, description="e.g. logistics, raw_materials")
    confidence: float = Field(..., ge=0, le=1)
    source_citation: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Event Publisher ──────────────────────────────────────────

class MacroPulseEventPublisher:
    """
    Publishes MacroPulse events to Redis pub/sub channels.
    Each event is JSON-serialized and published to the appropriate channel.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._publish_log: list[dict] = []

    async def _get_redis(self):
        """Lazy-load Redis client."""
        if self._redis is None:
            from app.core.redis_client import get_redis
            self._redis = await get_redis()
        return self._redis

    async def publish(self, event: BaseEvent) -> dict[str, Any]:
        """Publish an event to its designated Redis channel."""
        redis = await self._get_redis()
        channel = event.channel
        payload = event.model_dump_json()

        try:
            subscriber_count = await redis.publish(channel, payload)
            result = {
                "success": True,
                "event_id": event.event_id,
                "channel": channel,
                "consumer": CHANNEL_CONSUMERS.get(channel, "unknown"),
                "subscriber_count": subscriber_count,
                "timestamp": event.timestamp.isoformat(),
                "payload_bytes": len(payload),
            }
            self._publish_log.append(result)
            logger.info(
                "Published %s to %s (%d subscribers)",
                event.event_type, channel, subscriber_count,
            )
            return result
        except Exception as exc:
            logger.error("Failed to publish %s to %s: %s", event.event_type, channel, exc)
            return {
                "success": False,
                "event_id": event.event_id,
                "channel": channel,
                "error": str(exc),
            }

    async def publish_currency_signal(
        self,
        tenant_id: str,
        currency_pair: str,
        signal_type: str,
        magnitude_pct: float,
        direction: str,
        confidence: float,
        source_citation: str = "",
        recommended_action: str = "",
        **kwargs,
    ) -> dict:
        """Convenience method for publishing currency signals to GeoRisk."""
        event = CurrencySignalEvent(
            tenant_id=tenant_id,
            currency_pair=currency_pair,
            signal_type=signal_type,
            magnitude_pct=magnitude_pct,
            direction=direction,
            confidence=confidence,
            source_citation=source_citation,
            recommended_action=recommended_action,
            metadata=kwargs,
        )
        return await self.publish(event)

    async def publish_slowdown_risk(
        self,
        tenant_id: str,
        risk_level: str,
        risk_score: float,
        confidence: float,
        indicators: list[str] | None = None,
        affected_regions: list[str] | None = None,
        **kwargs,
    ) -> dict:
        """Convenience method for publishing slowdown risk to ChurnGuard."""
        event = SlowdownRiskEvent(
            tenant_id=tenant_id,
            risk_level=risk_level,
            risk_score=risk_score,
            confidence=confidence,
            indicators=indicators or [],
            affected_regions=affected_regions or [],
            gdp_growth_delta_pct=kwargs.pop("gdp_growth_delta_pct", 0.0),
            inflation_trend=kwargs.pop("inflation_trend", "stable"),
            interest_rate_direction=kwargs.pop("interest_rate_direction", "hold"),
            metadata=kwargs,
        )
        return await self.publish(event)

    async def publish_commodity_inflation(
        self,
        tenant_id: str,
        commodity: str,
        price_change_pct: float,
        direction: str,
        confidence: float,
        current_price_usd: float = 0.0,
        impact_on_cogs_pct: float = 0.0,
        affected_cost_categories: list[str] | None = None,
        **kwargs,
    ) -> dict:
        """Convenience method for publishing commodity inflation to SLAMonitor."""
        event = CommodityInflationEvent(
            tenant_id=tenant_id,
            commodity=commodity,
            price_change_pct=price_change_pct,
            direction=direction,
            confidence=confidence,
            current_price_usd=current_price_usd,
            impact_on_cogs_pct=impact_on_cogs_pct,
            affected_cost_categories=affected_cost_categories or [],
            metadata=kwargs,
        )
        return await self.publish(event)

    def get_publish_log(self) -> list[dict]:
        """Return recent publish log for observability."""
        return list(self._publish_log[-100:])


# ── Singleton ────────────────────────────────────────────────

_publisher_instance: MacroPulseEventPublisher | None = None


async def get_event_publisher() -> MacroPulseEventPublisher:
    """Get or create the singleton event publisher."""
    global _publisher_instance
    if _publisher_instance is None:
        _publisher_instance = MacroPulseEventPublisher()
    return _publisher_instance


# ── Event Schema Documentation Helper ────────────────────────

def get_event_schemas() -> dict[str, Any]:
    """Return documented event schemas for all pub/sub channels."""
    return {
        "channels": {
            MacroPulseChannel.CURRENCY_SIGNAL: {
                "description": "FX movement and currency risk signals",
                "consumer": "GeoRisk",
                "schema": CurrencySignalEvent.model_json_schema(),
            },
            MacroPulseChannel.SLOWDOWN_RISK: {
                "description": "Economic slowdown risk indicators",
                "consumer": "ChurnGuard",
                "schema": SlowdownRiskEvent.model_json_schema(),
            },
            MacroPulseChannel.COMMODITY_INFLATION: {
                "description": "Commodity price and inflation impact signals",
                "consumer": "SLAMonitor",
                "schema": CommodityInflationEvent.model_json_schema(),
            },
        },
        "version": "1.0",
        "source": "macropulse",
    }
