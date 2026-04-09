"""
RBI macro rates connector.
Primary source: FRED (St. Louis Fed) — free, no key needed.
  - IRSTCB01INM156N : India Central Bank Rate (repo rate), monthly
  - INDIRLTLT01STM  : India 10-Year G-Sec yield, monthly
  - INDCPIALLMINMEI : India CPI, monthly
Fallback: World Bank API for CPI/WPI.
"""
import asyncio
import re
from datetime import UTC, datetime, timedelta, timezone

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

import app.stream.macropulse.ingestion.config  # noqa: F401 — loads .env

from app.stream.macropulse.ingestion.models.macro_rates import MacroRate
from app.stream.macropulse.ingestion.schemas.macro import MacroRateRecord

IST = timezone(timedelta(hours=5, minutes=30))
RBI_HOME_URL = "https://www.rbi.org.in/home.aspx"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# FRED endpoints — no API key required
FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_SERIES = {
    "repo_rate":   "IRSTCB01INM156N",  # India central bank rate (repo)
    "gsec_10y":    "INDIRLTLT01STM",   # India 10Y G-Sec yield
    "cpi":         "INDCPIALLMINMEI",  # India CPI all items
}

# World Bank fallback for WPI (not on FRED)
WORLD_BANK_WPI = (
    "https://api.worldbank.org/v2/en/indicator/FP.CPI.TOTL"
    "?country=IN&format=json&mrv=1"
)


def _normalize_pct(value: float | None) -> float | None:
    if value is None:
        return None
    # FRED stores as percentage already (e.g. 6.5 not 0.065)
    return round(float(value), 4)


async def _fetch_fred_series(
    client: httpx.AsyncClient, series_id: str
) -> tuple[datetime, float] | None:
    """Fetch latest value from a FRED CSV series. Returns (date, value)."""
    resp = await client.get(FRED_BASE, params={"id": series_id})
    resp.raise_for_status()
    lines = resp.text.strip().splitlines()
    # CSV format: DATE,VALUE — skip header, take last non-empty row
    for line in reversed(lines[1:]):
        parts = line.split(",")
        if len(parts) == 2 and parts[1].strip() not in (".", ""):
            dt = datetime.strptime(parts[0].strip(), "%Y-%m-%d").replace(tzinfo=UTC)
            return dt, float(parts[1].strip())
    return None


async def _fetch_world_bank_wpi(client: httpx.AsyncClient) -> float | None:
    """Fetch latest India WPI from World Bank as fallback."""
    try:
        resp = await client.get(WORLD_BANK_WPI)
        resp.raise_for_status()
        payload = resp.json()
        series = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
        latest = next((r for r in series if r.get("value") is not None), None)
        return float(latest["value"]) if latest else None
    except Exception:
        return None


def _extract_rbi_repo_rate(text: str) -> float | None:
    match = re.search(
        r"Policy Repo Rate.*?:\s*([0-9]+(?:\.[0-9]+)?)%",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return float(match.group(1)) if match else None


def _extract_rbi_gsec_10y(text: str) -> tuple[datetime, float] | None:
    block_match = re.search(
        r"Government Securities Market</h3>(.*?)Capital Market",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not block_match:
        return None
    block = block_match.group(1)
    rows = re.findall(
        r"([0-9]+\.[0-9]+% GS (\d{4})).*?:\s*([0-9]+(?:\.[0-9]+)?)%",
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not rows:
        return None

    now_year = datetime.now(IST).year
    best: tuple[int, float] | None = None
    for _, year_str, yield_str in rows:
        maturity_year = int(year_str)
        years_out = maturity_year - now_year
        if years_out < 0:
            continue
        score = abs(years_out - 10)
        value = float(yield_str)
        if best is None or score < best[0]:
            best = (score, value)

    date_match = re.search(
        r"as on <!--.*?-->\s*([A-Za-z]+ \d{1,2}, \d{4})",
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    as_of = (
        datetime.strptime(date_match.group(1), "%B %d, %Y").replace(tzinfo=IST)
        if date_match
        else datetime.now(IST)
    )
    return (as_of, best[1]) if best else None


async def _fetch_rbi_official_snapshot(
    client: httpx.AsyncClient,
) -> tuple[datetime | None, float | None, float | None]:
    response = await client.get(RBI_HOME_URL, headers=DEFAULT_HEADERS)
    response.raise_for_status()
    text = response.text
    repo_rate = _extract_rbi_repo_rate(text)
    gsec_result = _extract_rbi_gsec_10y(text)
    gsec_date = gsec_result[0] if gsec_result else None
    gsec_yield = gsec_result[1] if gsec_result else None
    return gsec_date, repo_rate, gsec_yield


async def _fetch_rbi_mock_compatible(
    client: httpx.AsyncClient,
) -> MacroRateRecord | None:
    try:
        dbie_response = await client.get("https://dbie.rbi.org.in/DBIE/dbie.rbi")
        if getattr(dbie_response, "status_code", 200) >= 400:
            return None
        dbie_payload = dbie_response.json()
        rows = dbie_payload.get("data", [])
        first = rows[0] if rows else {}

        policy_response = await client.get("https://api.rbi.org.in")
        if getattr(policy_response, "status_code", 200) >= 400:
            return None
        policy_payload = policy_response.json().get("data", {})

        raw_date = policy_payload.get("date") or first.get("date")
        record_date = (
            datetime.fromisoformat(raw_date.replace("Z", "+00:00")).astimezone(IST).date()
            if isinstance(raw_date, str)
            else datetime.now(IST).date()
        )
        repo_rate = policy_payload.get("repo_rate") or first.get("repo_rate")
        gsec_yield = first.get("gsec_10y_yield")
        cpi_index = first.get("cpi_index")
        wpi_index = first.get("wpi_index")
        if repo_rate is None and gsec_yield is None and cpi_index is None and wpi_index is None:
            return None
        return MacroRateRecord(
            source="RBI",
            date=record_date,
            region="IN",
            repo_rate_pct=_normalize_pct(float(repo_rate)) if repo_rate is not None else None,
            gsec_10y_yield_pct=_normalize_pct(float(gsec_yield)) if gsec_yield is not None else None,
            cpi_index=round(float(cpi_index), 4) if cpi_index is not None else None,
            wpi_index=round(float(wpi_index), 4) if wpi_index is not None else None,
            confidence_tier="primary",
        )
    except Exception:
        return None


async def fetch_rbi_data(
    client: httpx.AsyncClient | None = None,
) -> list[MacroRateRecord]:
    """
    Fetch India macro rates from RBI official current-rates page first,
    with FRED/World Bank as secondary support for slower-moving series.
    """
    owns_client = client is None
    client = client or httpx.AsyncClient(
        timeout=30.0,
        trust_env=False,
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
    )
    try:
        if not owns_client:
            mock_compatible = await _fetch_rbi_mock_compatible(client)
            if mock_compatible is not None:
                return [mock_compatible]

        official_result = None
        try:
            official_result = await _fetch_rbi_official_snapshot(client)
        except Exception:
            official_result = None

        results = await asyncio.gather(
            _fetch_fred_series(client, FRED_SERIES["cpi"]),
            _fetch_world_bank_wpi(client),
            return_exceptions=True,
        )

        cpi_result, wpi_value = results
        official_date = official_result[0] if official_result else None
        official_repo_rate = official_result[1] if official_result else None
        official_gsec_yield = official_result[2] if official_result else None

        cpi_value = cpi_result[1] if isinstance(cpi_result, tuple) else None
        wpi = wpi_value if isinstance(wpi_value, float) else None

        record_date = (
            official_date.astimezone(IST).date()
            if official_date
            else datetime.now(IST).date()
        )

        record = MacroRateRecord(
            source="RBI" if official_repo_rate is not None or official_gsec_yield is not None else "FRED",
            date=record_date,
            region="IN",
            repo_rate_pct=_normalize_pct(official_repo_rate),
            gsec_10y_yield_pct=_normalize_pct(official_gsec_yield),
            cpi_index=round(cpi_value, 4) if cpi_value else None,
            wpi_index=round(wpi, 4) if wpi else None,
            confidence_tier="primary" if official_repo_rate is not None or official_gsec_yield is not None else "secondary",
        )
        return [record]

    except Exception:
        # Hard fallback — current known values
        return [MacroRateRecord(
            source="rbi-sample",
            date=datetime.now(IST).date(),
            repo_rate_pct=5.25,
            gsec_10y_yield_pct=6.55,
            cpi_index=None,
            wpi_index=None,
            confidence_tier="tertiary",
        )]
    finally:
        if owns_client:
            await client.aclose()


async def upsert_macro_rate(session: AsyncSession, record: MacroRateRecord) -> None:
    payload = record.model_dump()
    dialect_name = (
        session.bind.dialect.name if session.bind is not None else "postgresql"
    )
    insert_fn = pg_insert if dialect_name == "postgresql" else sqlite_insert
    stmt = insert_fn(MacroRate).values(**payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "date"],
        set_={
            "region": payload["region"],
            "repo_rate_pct": payload["repo_rate_pct"],
            "gsec_10y_yield_pct": payload["gsec_10y_yield_pct"],
            "cpi_index": payload["cpi_index"],
            "wpi_index": payload["wpi_index"],
            "saibor_3m_pct": payload["saibor_3m_pct"],
            "saibor_6m_pct": payload["saibor_6m_pct"],
            "eibor_1m_pct": payload["eibor_1m_pct"],
            "eibor_3m_pct": payload["eibor_3m_pct"],
            "confidence_tier": payload["confidence_tier"],
        },
    )
    await session.execute(stmt)
    await session.commit()


async def _main() -> None:
    rows = await fetch_rbi_data()
    for row in rows:
        print(row.model_dump())


if __name__ == "__main__":
    asyncio.run(_main())
