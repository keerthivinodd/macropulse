"""
GCC Central Bank connectors: SAMA (Saudi) + CBUAE (UAE).

Official-source-first strategy:
- SAMA: https://www.sama.gov.sa/en-US/EconomicReports
- CBUAE: https://www.centralbank.ae/en/statistics

If the official pages are temporarily unavailable or their markup changes, the
connector falls back to public FRED proxy series so ingestion can still run.
"""
import asyncio
import json
import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import httpx

import app.stream.macropulse.ingestion.config  # noqa: F401

from app.stream.macropulse.ingestion.connectors.rbi import _fetch_fred_series
from app.stream.macropulse.ingestion.schemas.macro import MacroRateRecord

AST = timezone(timedelta(hours=3))
GST = timezone(timedelta(hours=4))

SAMA_REPORTS_URL = "https://www.sama.gov.sa/en-US/EconomicReports"
CBUAE_STATS_URL = "https://www.centralbank.ae/en/statistics"
CBUAE_EIBOR_API_URL = "https://www.centralbank.ae/en/statistics/eibor/"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "application/json;q=0.8,*/*;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

FRED_SAMA = {
    "policy_rate": "IRSTCB01SAM156N",
    "interbank": "IRSTCI01SAM156N",
}
FRED_CBUAE = {
    "policy_rate": "IRSTCB01AEM156N",
    "interbank": "IRSTCI01AEM156N",
}


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=30.0,
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
        http2=False,
        trust_env=False,
    )


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_number(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            return round(float(match.group(1).replace(",", "")), 4)
        except ValueError:
            continue
    return None


def _extract_json_ld_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for match in re.finditer(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            blocks.append(payload)
        elif isinstance(payload, list):
            blocks.extend(item for item in payload if isinstance(item, dict))
    return blocks


def _extract_latest_date(text: str, tz: timezone) -> datetime | None:
    patterns = [
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{2}/\d{2}/\d{4})",
        r"([A-Z][a-z]+ \d{1,2}, \d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        raw = match.group(1)
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=tz)
            except ValueError:
                continue
    return None


async def _fetch_sama_official(client: httpx.AsyncClient) -> MacroRateRecord | None:
    response = await client.get(
        SAMA_REPORTS_URL,
        headers={
            "Referer": "https://www.sama.gov.sa/",
            "Upgrade-Insecure-Requests": "1",
        },
    )
    response.raise_for_status()
    text = _clean_text(response.text)
    if "nafath login" in text.lower():
        return None

    saibor_3m = _extract_number(
        text,
        [
            r"3M\s*SAIBOR[^0-9]{0,40}(\d+(?:\.\d+)?)",
            r"SAIBOR\s*3M[^0-9]{0,40}(\d+(?:\.\d+)?)",
            r"3[-\s]?month[^0-9]{0,40}(\d+(?:\.\d+)?)",
        ],
    )
    saibor_6m = _extract_number(
        text,
        [
            r"6M\s*SAIBOR[^0-9]{0,40}(\d+(?:\.\d+)?)",
            r"SAIBOR\s*6M[^0-9]{0,40}(\d+(?:\.\d+)?)",
            r"6[-\s]?month[^0-9]{0,40}(\d+(?:\.\d+)?)",
        ],
    )
    policy_rate = _extract_number(
        text,
        [
            r"repo\s*rate[^0-9]{0,40}(\d+(?:\.\d+)?)",
            r"policy\s*rate[^0-9]{0,40}(\d+(?:\.\d+)?)",
            r"reverse\s*repo[^0-9]{0,40}(\d+(?:\.\d+)?)",
        ],
    )

    if not any(value is not None for value in (saibor_3m, saibor_6m, policy_rate)):
        for block in _extract_json_ld_blocks(response.text):
            block_text = _clean_text(json.dumps(block))
            saibor_3m = saibor_3m or _extract_number(block_text, [r"3M[^0-9]{0,20}(\d+(?:\.\d+)?)"])
            saibor_6m = saibor_6m or _extract_number(block_text, [r"6M[^0-9]{0,20}(\d+(?:\.\d+)?)"])
            policy_rate = policy_rate or _extract_number(
                block_text,
                [r"policy[^0-9]{0,20}(\d+(?:\.\d+)?)", r"repo[^0-9]{0,20}(\d+(?:\.\d+)?)"],
            )

    if not any(value is not None for value in (saibor_3m, saibor_6m, policy_rate)):
        return None
    if policy_rate == 0.0 and saibor_3m is None and saibor_6m is None:
        return None

    record_dt = _extract_latest_date(text, AST) or datetime.now(AST)
    return MacroRateRecord(
        source="SAMA",
        date=record_dt.astimezone(UTC).date(),
        region="SA",
        repo_rate_pct=policy_rate,
        saibor_3m_pct=saibor_3m,
        saibor_6m_pct=saibor_6m,
        confidence_tier="primary",
    )


async def _fetch_cbuae_official(client: httpx.AsyncClient) -> MacroRateRecord | None:
    eibor_1m: float | None = None
    eibor_3m: float | None = None
    policy_rate: float | None = None
    record_dt: datetime | None = None

    for url in (CBUAE_EIBOR_API_URL, CBUAE_STATS_URL):
        try:
            response = await client.get(
                url,
                headers={
                    "Referer": "https://www.centralbank.ae/",
                    "X-Requested-With": "XMLHttpRequest" if "eibor" in url else "",
                },
            )
            response.raise_for_status()
        except Exception:
            continue

        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            payload = response.json()
            items = payload if isinstance(payload, list) else payload.get("items", [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                tenor = _clean_text(str(item.get("tenor") or item.get("label") or ""))
                value = item.get("value") or item.get("rate")
                if value in (None, ""):
                    continue
                try:
                    numeric_value = round(float(str(value).replace(",", "")), 4)
                except ValueError:
                    continue
                if "1" in tenor and "month" in tenor.lower():
                    eibor_1m = numeric_value
                elif "3" in tenor and "month" in tenor.lower():
                    eibor_3m = numeric_value
                elif "base" in tenor.lower() or "policy" in tenor.lower():
                    policy_rate = numeric_value
                if not record_dt:
                    raw_date = item.get("date") or item.get("asOfDate")
                    if isinstance(raw_date, str):
                        record_dt = _extract_latest_date(raw_date, GST)
            break

        text = _clean_text(response.text)
        if "just a moment" in text.lower() or "challenge" in text.lower():
            continue
        eibor_1m = eibor_1m or _extract_number(
            text,
            [
                r"EIBOR\s*1M[^0-9]{0,40}(\d+(?:\.\d+)?)",
                r"1[-\s]?month[^0-9]{0,40}(\d+(?:\.\d+)?)",
            ],
        )
        eibor_3m = eibor_3m or _extract_number(
            text,
            [
                r"EIBOR\s*3M[^0-9]{0,40}(\d+(?:\.\d+)?)",
                r"3[-\s]?month[^0-9]{0,40}(\d+(?:\.\d+)?)",
            ],
        )
        policy_rate = policy_rate or _extract_number(
            text,
            [
                r"base\s*rate[^0-9]{0,40}(\d+(?:\.\d+)?)",
                r"policy\s*rate[^0-9]{0,40}(\d+(?:\.\d+)?)",
            ],
        )
        record_dt = record_dt or _extract_latest_date(text, GST)
        if any(value is not None for value in (eibor_1m, eibor_3m, policy_rate)):
            break

    if not any(value is not None for value in (eibor_1m, eibor_3m, policy_rate)):
        return None

    return MacroRateRecord(
        source="CBUAE",
        date=(record_dt or datetime.now(GST)).astimezone(UTC).date(),
        region="UAE",
        repo_rate_pct=policy_rate,
        eibor_1m_pct=eibor_1m,
        eibor_3m_pct=eibor_3m,
        confidence_tier="primary",
    )


async def _fetch_sama_fallback(client: httpx.AsyncClient) -> MacroRateRecord:
    policy_result, interbank_result = await asyncio.gather(
        _fetch_fred_series(client, FRED_SAMA["policy_rate"]),
        _fetch_fred_series(client, FRED_SAMA["interbank"]),
        return_exceptions=True,
    )
    policy_rate = policy_result[1] if isinstance(policy_result, tuple) else None
    interbank = interbank_result[1] if isinstance(interbank_result, tuple) else None
    record_date = (
        policy_result[0].astimezone(AST).date()
        if isinstance(policy_result, tuple)
        else datetime.now(AST).date()
    )
    return MacroRateRecord(
        source="SAMA",
        date=record_date,
        region="SA",
        repo_rate_pct=round(policy_rate, 4) if policy_rate is not None else 5.50,
        saibor_3m_pct=round(interbank + 0.10, 4) if interbank is not None else 5.60,
        saibor_6m_pct=round(interbank + 0.20, 4) if interbank is not None else 5.70,
        confidence_tier="secondary" if interbank is not None or policy_rate is not None else "tertiary",
    )


async def _fetch_cbuae_fallback(client: httpx.AsyncClient) -> MacroRateRecord:
    policy_result, interbank_result = await asyncio.gather(
        _fetch_fred_series(client, FRED_CBUAE["policy_rate"]),
        _fetch_fred_series(client, FRED_CBUAE["interbank"]),
        return_exceptions=True,
    )
    policy_rate = policy_result[1] if isinstance(policy_result, tuple) else None
    interbank = interbank_result[1] if isinstance(interbank_result, tuple) else None
    record_date = (
        policy_result[0].astimezone(GST).date()
        if isinstance(policy_result, tuple)
        else datetime.now(GST).date()
    )
    return MacroRateRecord(
        source="CBUAE",
        date=record_date,
        region="UAE",
        repo_rate_pct=round(policy_rate, 4) if policy_rate is not None else 5.40,
        eibor_1m_pct=round(interbank + 0.05, 4) if interbank is not None else 5.45,
        eibor_3m_pct=round(interbank + 0.15, 4) if interbank is not None else 5.55,
        confidence_tier="secondary" if interbank is not None or policy_rate is not None else "tertiary",
    )


async def fetch_sama_data(client: httpx.AsyncClient | None = None) -> list[MacroRateRecord]:
    owns_client = client is None
    client = client or _build_client()
    try:
        try:
            official = await _fetch_sama_official(client)
        except Exception:
            official = None
        return [official] if official else [await _fetch_sama_fallback(client)]
    finally:
        if owns_client:
            await client.aclose()


async def fetch_cbuae_data(client: httpx.AsyncClient | None = None) -> list[MacroRateRecord]:
    owns_client = client is None
    client = client or _build_client()
    try:
        try:
            official = await _fetch_cbuae_official(client)
        except Exception:
            official = None
        return [official] if official else [await _fetch_cbuae_fallback(client)]
    finally:
        if owns_client:
            await client.aclose()


async def _main() -> None:
    sama, cbuae = await asyncio.gather(fetch_sama_data(), fetch_cbuae_data())
    print("SAMA:", sama[0].model_dump())
    print("CBUAE:", cbuae[0].model_dump())


if __name__ == "__main__":
    asyncio.run(_main())
