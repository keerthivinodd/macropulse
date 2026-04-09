from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
import xml.etree.ElementTree as ET

import httpx
import pandas as pd

from app.stream.macropulse.schemas import (
    MacroPulseIndicator,
    MacroPulseRealtimeResponse,
    MacroPulseSourceStatus,
)


ECB_HISTORY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
TREASURY_YIELD_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve"
BLS_SERIES_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0"


@dataclass
class TreasurySnapshot:
    ten_year: float
    ten_year_delta_bps: float
    spread_2s10s: float
    spread_delta_bps: float
    as_of: datetime


@dataclass
class EcbSnapshot:
    eur_usd: float
    pct_change: float
    as_of: datetime


@dataclass
class BlsSnapshot:
    cpi_index: float
    cpi_yoy: float
    cpi_mom: float
    as_of: datetime


class MacroPulseService:
    _cached_snapshot: MacroPulseRealtimeResponse | None = None

    def __init__(self) -> None:
        self.timeout = httpx.Timeout(6.0, connect=3.0)

    async def get_realtime_snapshot(self) -> MacroPulseRealtimeResponse:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                treasury, ecb, bls = await self._load_snapshots(client)
        except Exception:
            if self.__class__._cached_snapshot is not None:
                return self._fallback_snapshot(self.__class__._cached_snapshot)
            return self._default_fallback_snapshot()

        indicators = [
            MacroPulseIndicator(
                key="eurusd",
                symbol="EUR / USD",
                label="ECB Reference Rate",
                value=f"{ecb.eur_usd:.4f}",
                sub="Euro reference rate against the U.S. dollar",
                change=self._format_percent(ecb.pct_change),
                dir=self._direction(ecb.pct_change),
                source="ECB",
                as_of=ecb.as_of,
            ),
            MacroPulseIndicator(
                key="ust10y",
                symbol="US 10Y Yield",
                label="Daily Treasury Yield",
                value=f"{treasury.ten_year:.2f}%",
                sub="Official Treasury par yield curve rate",
                change=self._format_bps(treasury.ten_year_delta_bps),
                dir=self._direction(treasury.ten_year_delta_bps),
                source="U.S. Treasury",
                as_of=treasury.as_of,
            ),
            MacroPulseIndicator(
                key="spread_2s10s",
                symbol="2Y / 10Y Spread",
                label="Curve Steepness",
                value=f"{treasury.spread_2s10s:+.2f}%",
                sub="10-year minus 2-year Treasury spread",
                change=self._format_bps(treasury.spread_delta_bps),
                dir=self._direction(treasury.spread_delta_bps),
                source="U.S. Treasury",
                as_of=treasury.as_of,
            ),
            MacroPulseIndicator(
                key="us_cpi",
                symbol="US CPI",
                label="BLS Inflation Print",
                value=f"{bls.cpi_yoy:.2f}% YoY",
                sub=f"Monthly CPI index {bls.cpi_index:.3f} | {bls.cpi_mom:.2f}% MoM",
                change=self._format_percent(bls.cpi_mom),
                dir=self._direction(bls.cpi_mom),
                source="BLS",
                as_of=bls.as_of,
            ),
        ]

        market_confidence_score = self._market_confidence_score(
            treasury=treasury,
            ecb=ecb,
            bls=bls,
        )
        global_sentiment_change = round(
            (ecb.pct_change * 1.4) - (abs(treasury.ten_year_delta_bps) * 0.03) - max(bls.cpi_mom, 0) * 0.8,
            2,
        )

        headline = self._headline(treasury=treasury, ecb=ecb, bls=bls)
        narrative = self._narrative(treasury=treasury, ecb=ecb, bls=bls)
        confidence = round(min(98.0, 88.0 + abs(global_sentiment_change) + abs(treasury.spread_delta_bps) * 0.04), 1)

        snapshot = MacroPulseRealtimeResponse(
            headline=headline,
            narrative=narrative,
            anomaly_confidence=confidence,
            market_confidence_score=market_confidence_score,
            global_sentiment_change=global_sentiment_change,
            generated_at=datetime.now(UTC),
            indicators=indicators,
            sources=[
                MacroPulseSourceStatus(
                    name="European Central Bank FX Feed",
                    status="live",
                    latency="Daily",
                    coverage="EUR/USD reference rates",
                ),
                MacroPulseSourceStatus(
                    name="U.S. Treasury Yield Curve",
                    status="live",
                    latency="Daily close",
                    coverage="2Y, 10Y, and curve spreads",
                ),
                MacroPulseSourceStatus(
                    name="BLS CPI Public API",
                    status="live",
                    latency="Monthly release",
                    coverage="U.S. inflation benchmark",
                ),
            ],
        )
        self.__class__._cached_snapshot = snapshot
        return snapshot

    def _fallback_snapshot(self, snapshot: MacroPulseRealtimeResponse) -> MacroPulseRealtimeResponse:
        return snapshot.model_copy(
            update={
                "narrative": (
                    f"{snapshot.narrative} Live source refresh is temporarily unavailable, "
                    "so MacroPulse is showing the last successful official snapshot."
                ),
                "sources": [
                    source.model_copy(update={"status": "fallback"})
                    for source in snapshot.sources
                ],
            }
        )

    def _default_fallback_snapshot(self) -> MacroPulseRealtimeResponse:
        reference_time = datetime.now(UTC)
        return MacroPulseRealtimeResponse(
            headline="MacroPulse is showing the latest retained official-style macro snapshot.",
            narrative=(
                "Official source refresh is temporarily unavailable, so MacroPulse is using a built-in "
                "fallback snapshot until live retrieval succeeds again."
            ),
            anomaly_confidence=84.0,
            market_confidence_score=8.3,
            global_sentiment_change=0.31,
            generated_at=reference_time,
            indicators=[
                MacroPulseIndicator(
                    key="eurusd",
                    symbol="EUR / USD",
                    label="ECB Reference Rate",
                    value="1.1721",
                    sub="Euro reference rate against the U.S. dollar",
                    change="+0.49%",
                    dir="up",
                    source="ECB",
                    as_of=datetime(2026, 1, 2, tzinfo=UTC),
                ),
                MacroPulseIndicator(
                    key="ust10y",
                    symbol="US 10Y Yield",
                    label="Daily Treasury Yield",
                    value="8.02%",
                    sub="Official Treasury par yield curve rate",
                    change="+0.0 bp",
                    dir="neutral",
                    source="U.S. Treasury",
                    as_of=datetime(1991, 3, 14, tzinfo=UTC),
                ),
                MacroPulseIndicator(
                    key="spread_2s10s",
                    symbol="2Y / 10Y Spread",
                    label="Curve Steepness",
                    value="+1.07%",
                    sub="10-year minus 2-year Treasury spread",
                    change="+5.0 bp",
                    dir="up",
                    source="U.S. Treasury",
                    as_of=datetime(1991, 3, 14, tzinfo=UTC),
                ),
                MacroPulseIndicator(
                    key="us_cpi",
                    symbol="US CPI",
                    label="BLS Inflation Print",
                    value="2.41% YoY",
                    sub="Monthly CPI index 326.785 | 0.47% MoM",
                    change="+0.47%",
                    dir="up",
                    source="BLS",
                    as_of=datetime(2026, 2, 1, tzinfo=UTC),
                ),
            ],
            sources=[
                MacroPulseSourceStatus(
                    name="European Central Bank FX Feed",
                    status="fallback",
                    latency="Daily",
                    coverage="EUR/USD reference rates",
                ),
                MacroPulseSourceStatus(
                    name="U.S. Treasury Yield Curve",
                    status="fallback",
                    latency="Daily close",
                    coverage="2Y, 10Y, and curve spreads",
                ),
                MacroPulseSourceStatus(
                    name="BLS CPI Public API",
                    status="fallback",
                    latency="Monthly release",
                    coverage="U.S. inflation benchmark",
                ),
            ],
        )

    async def _load_snapshots(self, client: httpx.AsyncClient) -> tuple[TreasurySnapshot, EcbSnapshot, BlsSnapshot]:
        treasury_resp, ecb_resp, bls_resp = await asyncio.gather(
            client.get(TREASURY_YIELD_URL),
            client.get(ECB_HISTORY_URL),
            client.get(BLS_SERIES_URL),
        )
        treasury_resp.raise_for_status()
        ecb_resp.raise_for_status()
        bls_resp.raise_for_status()
        return (
            self._parse_treasury(treasury_resp.text),
            self._parse_ecb(ecb_resp.text),
            self._parse_bls(bls_resp.json()),
        )

    def _parse_treasury(self, html: str) -> TreasurySnapshot:
        tables = pd.read_html(StringIO(html))
        table = next(
            df for df in tables
            if "Date" in df.columns and "10 Yr" in df.columns and "2 Yr" in df.columns
        ).copy()
        table = table.replace("N/A", pd.NA).dropna(subset=["10 Yr", "2 Yr"])
        table["Date"] = pd.to_datetime(table["Date"], errors="coerce")
        table["10 Yr"] = pd.to_numeric(table["10 Yr"], errors="coerce")
        table["2 Yr"] = pd.to_numeric(table["2 Yr"], errors="coerce")
        table = table.dropna(subset=["Date", "10 Yr", "2 Yr"]).sort_values("Date")
        latest = table.iloc[-1]
        previous = table.iloc[-2] if len(table) > 1 else latest
        latest_spread = float(latest["10 Yr"] - latest["2 Yr"])
        previous_spread = float(previous["10 Yr"] - previous["2 Yr"])
        return TreasurySnapshot(
            ten_year=float(latest["10 Yr"]),
            ten_year_delta_bps=round((float(latest["10 Yr"]) - float(previous["10 Yr"])) * 100, 1),
            spread_2s10s=round(latest_spread, 2),
            spread_delta_bps=round((latest_spread - previous_spread) * 100, 1),
            as_of=latest["Date"].to_pydatetime().replace(tzinfo=UTC),
        )

    def _parse_ecb(self, xml_text: str) -> EcbSnapshot:
        root = ET.fromstring(xml_text)
        ns = {"gesmes": "http://www.gesmes.org/xml/2002-08-01", "def": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}
        cubes = root.findall(".//def:Cube[@time]", ns)
        if len(cubes) < 2:
            raise ValueError("ECB response did not contain enough historical points")

        def usd_rate(cube: ET.Element) -> float:
            for child in cube.findall("def:Cube", ns):
                if child.attrib.get("currency") == "USD":
                    return float(child.attrib["rate"])
            raise ValueError("USD rate missing from ECB response")

        latest_cube, previous_cube = cubes[-1], cubes[-2]
        latest_rate = usd_rate(latest_cube)
        previous_rate = usd_rate(previous_cube)
        pct_change = ((latest_rate - previous_rate) / previous_rate) * 100 if previous_rate else 0.0
        return EcbSnapshot(
            eur_usd=latest_rate,
            pct_change=round(pct_change, 3),
            as_of=datetime.fromisoformat(latest_cube.attrib["time"]).replace(tzinfo=UTC),
        )

    def _parse_bls(self, payload: dict) -> BlsSnapshot:
        series = payload["Results"]["series"][0]["data"]
        monthly = [item for item in series if item["period"].startswith("M") and item["period"] != "M13"]
        latest = monthly[0]
        previous = monthly[1]
        year_back = next(
            item for item in monthly[1:]
            if item["period"] == latest["period"] and item["year"] != latest["year"]
        )
        latest_value = float(latest["value"])
        previous_value = float(previous["value"])
        year_back_value = float(year_back["value"])
        cpi_mom = ((latest_value - previous_value) / previous_value) * 100 if previous_value else 0.0
        cpi_yoy = ((latest_value - year_back_value) / year_back_value) * 100 if year_back_value else 0.0
        month = int(latest["period"][1:])
        as_of = datetime(int(latest["year"]), month, 1, tzinfo=UTC)
        return BlsSnapshot(
            cpi_index=latest_value,
            cpi_yoy=round(cpi_yoy, 2),
            cpi_mom=round(cpi_mom, 2),
            as_of=as_of,
        )

    def _format_percent(self, value: float) -> str:
        return f"{value:+.2f}%"

    def _format_bps(self, value: float) -> str:
        return f"{value:+.1f} bp"

    def _direction(self, value: float) -> str:
        if value > 0:
            return "up"
        if value < 0:
            return "down"
        return "neutral"

    def _headline(self, treasury: TreasurySnapshot, ecb: EcbSnapshot, bls: BlsSnapshot) -> str:
        if bls.cpi_yoy >= 3.0 and treasury.ten_year >= 4.0:
            return "Inflation remains firm while long-end rates stay elevated."
        if treasury.spread_2s10s < 0:
            return "Yield curve inversion persists despite stable cross-market pricing."
        if ecb.pct_change >= 0.4:
            return "Euro strength is emerging as a live macro driver for dollar-based planning."
        return "Macro conditions are stable, but finance teams should monitor rates and inflation closely."

    def _narrative(self, treasury: TreasurySnapshot, ecb: EcbSnapshot, bls: BlsSnapshot) -> str:
        return (
            f"Latest official feeds show the U.S. 10Y yield at {treasury.ten_year:.2f}% "
            f"with a 2Y/10Y spread of {treasury.spread_2s10s:+.2f}%. "
            f"EUR/USD moved {ecb.pct_change:+.2f}% day over day, while BLS CPI printed "
            f"{bls.cpi_yoy:.2f}% year over year and {bls.cpi_mom:.2f}% month over month."
        )

    def _market_confidence_score(self, treasury: TreasurySnapshot, ecb: EcbSnapshot, bls: BlsSnapshot) -> float:
        score = 8.7
        score -= min(abs(treasury.ten_year_delta_bps) / 40, 1.2)
        score -= min(abs(ecb.pct_change) / 1.5, 0.8)
        score -= min(max(bls.cpi_yoy - 2.2, 0) / 2.0, 1.2)
        if treasury.spread_2s10s < 0:
            score -= 0.5
        return round(max(1.0, min(score, 9.9)), 1)
