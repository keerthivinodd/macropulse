# MacroPulse Pub/Sub Event Schemas

Redis pub/sub channels for cross-module reusability. Each MacroPulse output event is published as JSON to the designated channel.

---

## Channels Overview

| Channel                     | Consumer    | Description                                |
|-----------------------------|-------------|-------------------------------------------|
| `macro.currency_signal`     | GeoRisk     | FX movements, central bank policy changes |
| `macro.slowdown_risk`       | ChurnGuard  | Economic slowdown risk indicators         |
| `macro.commodity_inflation` | SLAMonitor  | Commodity price & inflation impact        |

---

## Common Envelope

Every event includes these base fields:

```json
{
  "event_id": "string (uuid hex)",
  "event_type": "string",
  "channel": "string",
  "tenant_id": "string",
  "timestamp": "ISO 8601 datetime",
  "source": "macropulse",
  "version": "1.0"
}
```

---

## 1. `macro.currency_signal` → GeoRisk

Fired when MacroPulse detects significant FX movement, central bank policy change, or currency risk signal.

```json
{
  "event_id": "a1b2c3d4...",
  "event_type": "currency_signal",
  "channel": "macro.currency_signal",
  "tenant_id": "tenant-india-001",
  "timestamp": "2026-04-03T10:30:00Z",
  "source": "macropulse",
  "version": "1.0",

  "currency_pair": "USD/INR",
  "signal_type": "depreciation | appreciation | volatility_spike | policy_change",
  "magnitude_pct": 1.25,
  "direction": "up | down | mixed",
  "confidence": 0.88,
  "source_citation": "RBI Reference Rate • 2026-04-03",
  "recommended_action": "Review unhedged USD receivables",
  "metadata": {}
}
```

**Fields:**

| Field                | Type    | Required | Description                                |
|---------------------|---------|----------|--------------------------------------------|
| `currency_pair`     | string  | Yes      | e.g. `USD/INR`, `AED/INR`                 |
| `signal_type`       | string  | Yes      | One of: depreciation, appreciation, volatility_spike, policy_change |
| `magnitude_pct`     | float   | Yes      | Percentage change or z-score               |
| `direction`         | string  | Yes      | `up`, `down`, or `mixed`                   |
| `confidence`        | float   | Yes      | 0.0–1.0                                   |
| `source_citation`   | string  | No       | Data source reference                      |
| `recommended_action`| string  | No       | Suggested hedging or action                |
| `metadata`          | object  | No       | Additional context                         |

---

## 2. `macro.slowdown_risk` → ChurnGuard

Fired when macro indicators suggest economic slowdown risk that could impact customer retention.

```json
{
  "event_id": "e5f6g7h8...",
  "event_type": "slowdown_risk",
  "channel": "macro.slowdown_risk",
  "tenant_id": "tenant-india-001",
  "timestamp": "2026-04-03T10:30:00Z",
  "source": "macropulse",
  "version": "1.0",

  "risk_level": "high",
  "risk_score": 72.5,
  "indicators": ["gdp_growth_decline", "rising_inflation", "rate_hike"],
  "gdp_growth_delta_pct": -0.8,
  "inflation_trend": "rising",
  "interest_rate_direction": "hike",
  "affected_regions": ["India", "South Asia"],
  "confidence": 0.82,
  "metadata": {}
}
```

**Fields:**

| Field                     | Type     | Required | Description                                |
|--------------------------|----------|----------|--------------------------------------------|
| `risk_level`             | string   | Yes      | `low`, `medium`, `high`, `critical`        |
| `risk_score`             | float    | Yes      | Composite score 0–100                      |
| `indicators`             | string[] | No       | Contributing macro indicators              |
| `gdp_growth_delta_pct`   | float    | No       | GDP growth change vs prior quarter         |
| `inflation_trend`        | string   | No       | `rising`, `falling`, `stable`              |
| `interest_rate_direction`| string   | No       | `hike`, `cut`, `hold`                      |
| `affected_regions`       | string[] | No       | Regions with elevated risk                 |
| `confidence`             | float    | Yes      | 0.0–1.0                                   |
| `metadata`               | object   | No       | Additional context                         |

---

## 3. `macro.commodity_inflation` → SLAMonitor

Fired when commodity price movements could impact cost structures and SLA pricing.

```json
{
  "event_id": "i9j0k1l2...",
  "event_type": "commodity_inflation",
  "channel": "macro.commodity_inflation",
  "tenant_id": "tenant-india-001",
  "timestamp": "2026-04-03T10:30:00Z",
  "source": "macropulse",
  "version": "1.0",

  "commodity": "brent_crude",
  "price_change_pct": 3.2,
  "current_price_usd": 82.50,
  "direction": "up",
  "impact_on_cogs_pct": 1.8,
  "affected_cost_categories": ["logistics", "raw_materials"],
  "confidence": 0.85,
  "source_citation": "EIA Brent Crude • 2026-04-03",
  "metadata": {}
}
```

**Fields:**

| Field                       | Type     | Required | Description                                |
|----------------------------|----------|----------|--------------------------------------------|
| `commodity`                | string   | Yes      | e.g. `brent_crude`, `gold`, `natural_gas`  |
| `price_change_pct`         | float    | Yes      | MoM price change %                         |
| `current_price_usd`        | float    | No       | Current price in USD                       |
| `direction`                | string   | Yes      | `up` or `down`                             |
| `impact_on_cogs_pct`       | float    | No       | Estimated COGS impact %                    |
| `affected_cost_categories` | string[] | No       | e.g. `logistics`, `raw_materials`          |
| `confidence`               | float    | Yes      | 0.0–1.0                                   |
| `source_citation`          | string   | No       | Data source reference                      |
| `metadata`                 | object   | No       | Additional context                         |

---

## Subscribing to Events

### Python (redis-py async)

```python
import redis.asyncio as aioredis
import json

redis = aioredis.from_url("redis://localhost:6379/0")
pubsub = redis.pubsub()
await pubsub.subscribe("macro.currency_signal", "macro.slowdown_risk", "macro.commodity_inflation")

async for message in pubsub.listen():
    if message["type"] == "message":
        event = json.loads(message["data"])
        print(f"[{event['channel']}] {event['event_type']} — confidence: {event['confidence']}")
```

### Publishing (via MacroPulseEventPublisher)

```python
from app.stream.macropulse.event_publisher import get_event_publisher

publisher = await get_event_publisher()

# Currency signal → GeoRisk
await publisher.publish_currency_signal(
    tenant_id="tenant-india-001",
    currency_pair="USD/INR",
    signal_type="depreciation",
    magnitude_pct=1.25,
    direction="up",
    confidence=0.88,
)

# Slowdown risk → ChurnGuard
await publisher.publish_slowdown_risk(
    tenant_id="tenant-india-001",
    risk_level="high",
    risk_score=72.5,
    confidence=0.82,
    indicators=["gdp_growth_decline", "rising_inflation"],
)

# Commodity inflation → SLAMonitor
await publisher.publish_commodity_inflation(
    tenant_id="tenant-india-001",
    commodity="brent_crude",
    price_change_pct=3.2,
    direction="up",
    confidence=0.85,
    current_price_usd=82.50,
)
```
