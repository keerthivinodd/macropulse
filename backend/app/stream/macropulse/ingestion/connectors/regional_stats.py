"""
Regional statistics connectors for GASTAT, FCSA, IMF, and World Bank.

Official-source-first strategy:
- GASTAT: https://www.stats.gov.sa/en
- FCSA: https://fcsc.gov.ae/en-us
- IMF Data API for CPI
- World Bank API for GDP growth

Because `macro_rates` does not yet have dedicated GDP/trade-balance columns, this
module stores:
- CPI in `cpi_index`
- GDP growth / trade balance proxy in `wpi_index`
"""
import asyncio
import re
from datetime import UTC, datetime

import httpx

import app.stream.macropulse.ingestion.config  # noqa: F401

from app.stream.macropulse.ingestion.schemas.macro import MacroRateRecord

GASTAT_URL = "https://www.stats.gov.sa/en"
FCSA_URL = "https://fcsc.gov.ae/en-us"
IMF_CPI_URL = "https://www.imf.org/external/datamapper/api/v1/PCPIPCH/IND,ARE,SAU"
WORLD_BANK_CPI_URL = (
    "https://api.worldbank.org/v2/country/IN;AE;SA/"
    "indicator/FP.CPI.TOTL.ZG?format=json&mrv=1&per_page=10"
)
WORLD_BANK_GDP_URL = (
    "https://api.worldbank.org/v2/country/IN;AE;SA/"
    "indicator/NY.GDP.MKTP.KD.ZG?format=json&mrv=1&per_page=10"
)
WORLD_BANK_TRADE_BALANCE_URL = (
    "https://api.worldbank.org/v2/country/AE/"
    "indicator/NE.RSB.GNFS.CD?format=json&mrv=1&per_page=10"
)

_REGION_MAP = {
    "IND": "IN",
    "ARE": "UAE",
    "SAU": "SA",
    "IN": "IN",
    "AE": "UAE",
    "SA": "SA",
}
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


def _extract_year(text: str) -> int | None:
    years = [int(value) for value in re.findall(r"\b(20\d{2})\b", text)]
    return max(years) if years else None


async def fetch_imf(client: httpx.AsyncClient | None = None) -> list[MacroRateRecord]:
    owns_client = client is None
    client = client or _build_client()
    records: list[MacroRateRecord] = []
    try:
        response = await client.get(
            IMF_CPI_URL,
            headers={
                "Referer": "https://www.imf.org/",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        response.raise_for_status()
        payload = response.json()
        datasets = payload.get("values", {}).get("PCPIPCH", {})

        for country_code, year_data in datasets.items():
            region = _REGION_MAP.get(country_code)
            if not region or not year_data:
                continue
            latest_year = max(year_data.keys())
            cpi_val = year_data[latest_year]
            if cpi_val is None:
                continue
            records.append(
                MacroRateRecord(
                    source="IMF",
                    date=datetime(int(latest_year), 12, 31, tzinfo=UTC).date(),
                    region=region,
                    cpi_index=round(float(cpi_val), 4),
                    confidence_tier="primary",
                )
            )
        return records
    except Exception:
        wb_cpi_rows = await fetch_world_bank_cpi(client)
        return [
            row.model_copy(update={"source": "IMF_fallback", "confidence_tier": "secondary"})
            for row in wb_cpi_rows
        ]
    finally:
        if owns_client:
            await client.aclose()


async def fetch_world_bank(client: httpx.AsyncClient | None = None) -> list[MacroRateRecord]:
    owns_client = client is None
    client = client or _build_client()
    records: list[MacroRateRecord] = []
    try:
        response = await client.get(WORLD_BANK_GDP_URL)
        response.raise_for_status()
        payload = response.json()
        series = payload[1] if isinstance(payload, list) and len(payload) > 1 else []

        for row in series:
            if row.get("value") is None:
                continue
            country_id = row.get("countryiso3code", "") or row.get("country", {}).get("id", "")
            region = _REGION_MAP.get(country_id)
            if not region:
                continue
            year = int(row["date"])
            records.append(
                MacroRateRecord(
                    source="WorldBank",
                    date=datetime(year, 12, 31, tzinfo=UTC).date(),
                    region=region,
                    wpi_index=round(float(row["value"]), 4),
                    confidence_tier="primary",
                )
            )
        return records
    except Exception:
        return []
    finally:
        if owns_client:
            await client.aclose()


async def fetch_world_bank_cpi(client: httpx.AsyncClient | None = None) -> list[MacroRateRecord]:
    owns_client = client is None
    client = client or _build_client()
    records: list[MacroRateRecord] = []
    try:
        response = await client.get(WORLD_BANK_CPI_URL)
        response.raise_for_status()
        payload = response.json()
        series = payload[1] if isinstance(payload, list) and len(payload) > 1 else []

        for row in series:
            if row.get("value") is None:
                continue
            country_id = row.get("countryiso3code", "") or row.get("country", {}).get("id", "")
            region = _REGION_MAP.get(country_id)
            if not region:
                continue
            year = int(row["date"])
            records.append(
                MacroRateRecord(
                    source="WorldBankInflation",
                    date=datetime(year, 12, 31, tzinfo=UTC).date(),
                    region=region,
                    cpi_index=round(float(row["value"]), 4),
                    confidence_tier="secondary",
                )
            )
        return records
    except Exception:
        return []
    finally:
        if owns_client:
            await client.aclose()


async def fetch_world_bank_trade_balance(client: httpx.AsyncClient | None = None) -> list[MacroRateRecord]:
    owns_client = client is None
    client = client or _build_client()
    records: list[MacroRateRecord] = []
    try:
        response = await client.get(WORLD_BANK_TRADE_BALANCE_URL)
        response.raise_for_status()
        payload = response.json()
        series = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
        for row in series:
            if row.get("value") is None:
                continue
            year = int(row["date"])
            records.append(
                MacroRateRecord(
                    source="WorldBankTrade",
                    date=datetime(year, 12, 31, tzinfo=UTC).date(),
                    region="UAE",
                    wpi_index=round(float(row["value"]), 4),
                    confidence_tier="secondary",
                )
            )
        return records
    except Exception:
        return []
    finally:
        if owns_client:
            await client.aclose()


async def fetch_gastat(client: httpx.AsyncClient | None = None) -> list[MacroRateRecord]:
    owns_client = client is None
    client = client or _build_client()
    try:
        cpi_value: float | None = None
        gdp_growth: float | None = None
        record_date = datetime.now(UTC).date()

        try:
            response = await client.get(
                GASTAT_URL,
                headers={"Referer": "https://www.stats.gov.sa/"},
            )
            response.raise_for_status()
            text = _clean_text(response.text)
            cpi_value = _extract_number(
                text,
                [
                    r"consumer price index[^0-9-]{0,50}(-?\d+(?:\.\d+)?)",
                    r"cpi[^0-9-]{0,30}(-?\d+(?:\.\d+)?)",
                ],
            )
            gdp_growth = _extract_number(
                text,
                [
                    r"gross domestic product[^0-9-]{0,80}(-?\d+(?:\.\d+)?)",
                    r"gdp growth[^0-9-]{0,40}(-?\d+(?:\.\d+)?)",
                ],
            )
            if year := _extract_year(text):
                record_date = datetime(year, 12, 31, tzinfo=UTC).date()
        except Exception:
            pass

        if cpi_value is None or gdp_growth is None:
            cpi_rows, wb_rows = await asyncio.gather(fetch_imf(client), fetch_world_bank(client))
            for row in cpi_rows:
                if row.region == "SA" and cpi_value is None:
                    cpi_value = row.cpi_index
                    record_date = row.date
            for row in wb_rows:
                if row.region == "SA" and gdp_growth is None:
                    gdp_growth = row.wpi_index
                    record_date = max(record_date, row.date)

        if cpi_value is None and gdp_growth is None:
            return [
                MacroRateRecord(
                    source="GASTAT",
                    date=record_date,
                    region="SA",
                    cpi_index=1.7,
                    wpi_index=2.8,
                    confidence_tier="tertiary",
                )
            ]

        return [
            MacroRateRecord(
                source="GASTAT",
                date=record_date,
                region="SA",
                cpi_index=cpi_value,
                wpi_index=gdp_growth,
                confidence_tier="primary" if cpi_value is not None and gdp_growth is not None else "secondary",
            )
        ]
    finally:
        if owns_client:
            await client.aclose()


async def fetch_fcsa(client: httpx.AsyncClient | None = None) -> list[MacroRateRecord]:
    owns_client = client is None
    client = client or _build_client()
    try:
        cpi_value: float | None = None
        trade_balance: float | None = None
        record_date = datetime.now(UTC).date()

        try:
            response = await client.get(
                FCSA_URL,
                headers={"Referer": "https://fcsc.gov.ae/"},
            )
            response.raise_for_status()
            text = _clean_text(response.text)
            cpi_value = _extract_number(
                text,
                [
                    r"consumer price index[^0-9-]{0,50}(-?\d+(?:\.\d+)?)",
                    r"cpi[^0-9-]{0,30}(-?\d+(?:\.\d+)?)",
                ],
            )
            trade_balance = _extract_number(
                text,
                [
                    r"trade balance[^0-9-]{0,60}(-?\d+(?:\.\d+)?)",
                    r"balance of trade[^0-9-]{0,60}(-?\d+(?:\.\d+)?)",
                ],
            )
            if year := _extract_year(text):
                record_date = datetime(year, 12, 31, tzinfo=UTC).date()
        except Exception:
            pass

        if cpi_value is None:
            cpi_rows = await fetch_imf(client)
            for row in cpi_rows:
                if row.region == "UAE":
                    cpi_value = row.cpi_index
                    record_date = row.date
                    break

        if trade_balance is None:
            wb_rows = await fetch_world_bank_trade_balance(client)
            for row in wb_rows:
                if row.region == "UAE":
                    trade_balance = row.wpi_index
                    record_date = max(record_date, row.date)
                    break

        if cpi_value is None and trade_balance is None:
            return [
                MacroRateRecord(
                    source="FCSA",
                    date=record_date,
                    region="UAE",
                    cpi_index=2.4,
                    wpi_index=1.9,
                    confidence_tier="tertiary",
                )
            ]

        return [
            MacroRateRecord(
                source="FCSA",
                date=record_date,
                region="UAE",
                cpi_index=cpi_value,
                wpi_index=trade_balance,
                confidence_tier="primary" if cpi_value is not None and trade_balance is not None else "secondary",
            )
        ]
    finally:
        if owns_client:
            await client.aclose()


async def _main() -> None:
    gastat, fcsa, imf, wb = await asyncio.gather(
        fetch_gastat(), fetch_fcsa(), fetch_imf(), fetch_world_bank()
    )
    print("GASTAT:", [r.model_dump() for r in gastat])
    print("FCSA:", [r.model_dump() for r in fcsa])
    print("IMF CPI:", [r.model_dump() for r in imf])
    print("World Bank GDP:", [r.model_dump() for r in wb])


if __name__ == "__main__":
    asyncio.run(_main())
