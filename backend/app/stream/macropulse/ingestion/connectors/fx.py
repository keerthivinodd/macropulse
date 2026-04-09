import asyncio
import os
from datetime import UTC, datetime, time, timedelta, timezone

import httpx

import app.stream.macropulse.ingestion.config  # noqa: F401 — loads .env

from app.stream.macropulse.ingestion.schemas.macro import FxRateRecord

IST = timezone(timedelta(hours=5, minutes=30))
ALPHA_URL = "https://www.alphavantage.co/query"
OXR_URL = "https://openexchangerates.org/api/latest.json"
SAMPLE_FX_ROW = FxRateRecord(
    timestamp=datetime(2026, 4, 2, 10, 0, tzinfo=IST),
    usd_inr=83.25,
    aed_inr=22.67,
    sar_inr=22.20,
    source="sample",
    region="IN",
)


def is_market_hours(region: str, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    code = region.upper()
    if code == "IN":
        local = now.astimezone(IST)
        return time(9, 15) <= local.time() <= time(15, 30)
    if code == "GCC":
        local = now.astimezone(IST)
        return time(10, 0) <= local.time() <= time(18, 0)
    return True


async def fetch_fx_rates(client: httpx.AsyncClient | None = None) -> FxRateRecord:
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=20.0, trust_env=False)
    try:
        try:
            alpha_params = {
                "function": "FX_INTRADAY",
                "from_symbol": "USD",
                "to_symbol": "INR",
                "interval": "5min",
                "apikey": os.getenv("ALPHAVANTAGE_API_KEY", ""),
            }
            alpha_response = await client.get(ALPHA_URL, params=alpha_params)
            alpha_response.raise_for_status()
            alpha_payload = alpha_response.json()

            ts_key = next((key for key in alpha_payload if "Time Series" in key), None)
            if ts_key:
                series = alpha_payload[ts_key]
                latest_ts = max(series)
                usd_inr = float(series[latest_ts]["4. close"])
                timestamp = datetime.fromisoformat(latest_ts).replace(tzinfo=IST)
            else:
                latest_ts = None
                usd_inr = None
                timestamp = datetime.now(IST)

            oxr_response = await client.get(
                OXR_URL,
                params={
                    "app_id": os.getenv("OPEN_EXCHANGE_APP_ID", ""),
                    "symbols": "INR,AED,SAR",
                },
            )
            oxr_response.raise_for_status()
            oxr_payload = oxr_response.json()
            rates = oxr_payload["rates"]

            usd_inr = usd_inr or float(rates["INR"])
            aed_inr = round(float(rates["INR"]) / float(rates["AED"]), 6)
            sar_inr = round(float(rates["INR"]) / float(rates["SAR"]), 6)

            return FxRateRecord(
                timestamp=timestamp,
                usd_inr=usd_inr,
                aed_inr=aed_inr,
                sar_inr=sar_inr,
                source="alpha_vantage+open_exchange_rates" if latest_ts else "open_exchange_rates",
                region="IN",
            )
        except Exception:
            return SAMPLE_FX_ROW
    finally:
        if owns_client:
            await client.aclose()


async def _main() -> None:
    print((await fetch_fx_rates()).model_dump())


if __name__ == "__main__":
    asyncio.run(_main())
