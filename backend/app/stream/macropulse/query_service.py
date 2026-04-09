from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from app.stream.macropulse.anomaly import z_score_flags
from app.stream.macropulse.company_profile import DEFAULT_COMPANY_PROFILE
from app.stream.macropulse.confidence import compute_confidence
from app.stream.macropulse.schemas import (
    MacroPulseAgentQueryResponse,
    MacroPulseAgentSource,
    MacroPulseDashboardAlert,
    MacroPulseDashboardResponse,
    MacroPulseDashboardTile,
    MacroPulseRealtimeResponse,
    MacroPulseSensitivityRow,
)
from app.stream.macropulse.service import MacroPulseService
from app.stream.macropulse.tools.scenario_sim_tool import scenario_sim_tool
from app.stream.macropulse.tools.time_series_tool import time_series_tool


DEFAULT_SERIES = {
    "interest_rate": [6.0, 6.25, 6.5, 6.5, 6.5, 6.25, 6.5, 6.75],
    "fx": [81.2, 81.8, 82.1, 82.4, 82.9, 83.1, 83.4, 83.8],
    "commodity": [78.0, 79.5, 80.1, 81.4, 82.8, 83.6, 84.2, 85.1],
    "combined": [100.0, 101.2, 102.6, 103.1, 104.8, 106.4, 107.0, 108.9],
    "overview": [100.0, 100.4, 100.2, 100.9, 101.3, 101.0, 101.8, 102.1],
}


def _infer_query_type(text: str) -> str:
    normalized = text.lower()
    if any(keyword in normalized for keyword in ["combined", "worst case", "all shocks", "stress test"]):
        return "combined"
    if any(keyword in normalized for keyword in ["fx", "currency", "usd", "aed", "sar", "inr"]):
        return "fx"
    if any(keyword in normalized for keyword in ["oil", "commodity", "crude", "brent", "input cost"]):
        return "commodity"
    if any(keyword in normalized for keyword in ["rate", "repo", "yield", "borrowing", "interest"]):
        return "interest_rate"
    return "overview"


def _extract_first_number(text: str) -> float | None:
    match = re.search(r"(-?\d+(?:\.\d+)?)", text)
    if not match:
        return None
    return float(match.group(1))


def _scenario_kwargs(query_type: str, text: str) -> dict:
    extracted = _extract_first_number(text)
    if query_type == "interest_rate":
        return {"scenario_type": query_type, "rate_delta_pct": extracted or 0.5}
    if query_type == "fx":
        return {"scenario_type": query_type, "fx_delta_pct": extracted or 3.0}
    if query_type == "commodity":
        return {"scenario_type": query_type, "oil_delta_usd": extracted or 5.0}
    if query_type == "combined":
        shock = extracted or 2.0
        return {
            "scenario_type": query_type,
            "rate_delta_pct": shock,
            "fx_delta_pct": max(shock, 3.0),
            "oil_delta_usd": max(shock * 2, 5.0),
        }
    return {"scenario_type": "combined", "rate_delta_pct": 0.25, "fx_delta_pct": 1.5, "oil_delta_usd": 3.0}


def _recommended_action(query_type: str, publish_status: str) -> str:
    base = {
        "interest_rate": "Review floating-rate debt and refresh the treasury hedge plan.",
        "fx": "Validate hedge coverage on open currency exposure before the next close.",
        "commodity": "Revisit procurement buffers and margin protection thresholds.",
        "combined": "Escalate a cross-functional treasury and sourcing review within 24 hours.",
        "overview": "Monitor central-bank, FX, and commodity signals in the next planning cycle.",
    }[query_type]
    if publish_status == "hitl_queue":
        return f"{base} Route the draft to human review before publishing."
    if publish_status == "review":
        return f"{base} Add one more corroborating source before auto-distribution."
    return base


def _regional_context(region: str | None) -> str:
    selected = region or DEFAULT_COMPANY_PROFILE.primary_region
    currency = DEFAULT_COMPANY_PROFILE.primary_currency
    return f"Primary operating region: {selected}. Default reporting currency: {currency}."


async def build_agent_query_response(
    text: str,
    region: str | None = None,
    tenant_id: UUID | None = None,
) -> MacroPulseAgentQueryResponse:
    query_type = _infer_query_type(text)
    scenario_output = scenario_sim_tool(**_scenario_kwargs(query_type, text))
    series = DEFAULT_SERIES[query_type]
    analytics = {
        "time_series": time_series_tool(series, label=query_type),
        "anomaly": z_score_flags(series),
        "tenant_id": str(tenant_id) if tenant_id else None,
    }
    from app.stream.macropulse.tools.market_docs_retriever import market_docs_retriever
    retrieval = await market_docs_retriever(query=text, region=region)
    matches = retrieval.get("matches", [])
    independent_sources = retrieval.get("independent_sources", 0)
    primary_source_ok = len(matches) > 0
    market_data_ok = any(m["score"] > 0.4 for m in matches)
    news_corroboration_ok = independent_sources >= 2
    conflict_detected = "conflict" in text.lower() or (
        len(matches) >= 2 and abs(matches[0]["score"] - matches[1]["score"]) < 0.05
    )
    confidence = compute_confidence(
        primary_source_ok=primary_source_ok,
        market_data_ok=market_data_ok,
        news_corroboration_ok=news_corroboration_ok,
        independent_sources=independent_sources,
        conflict_detected=conflict_detected,
    )


    sources = [
        MacroPulseAgentSource(
            name="MacroPulse Scenario Engine",
            category="model",
            detail="Deterministic financial stress model using the default tenant profile.",
        ),
        MacroPulseAgentSource(
            name="Market KPI Series",
            category="market",
            detail=f"Synthetic {query_type} monitoring series prepared for the current build.",
        ),
    ]
    if query_type in {"interest_rate", "overview"}:
        sources.append(
            MacroPulseAgentSource(
                name="Central Bank Policy Feed",
                category="official",
                detail="Official policy and benchmark rate context is required for this answer.",
            )
        )
    else:
        sources.append(
            MacroPulseAgentSource(
                name="Regional Macro News",
                category="news",
                detail="Regional macro coverage provides qualitative corroboration for the signal.",
            )
        )

    return MacroPulseAgentQueryResponse(
        query_type=query_type,
        impact=scenario_output["headline"],
        confidence=confidence.score,
        publish_status=confidence.publish_status,
        recommended_action=_recommended_action(query_type, confidence.publish_status),
        sources=sources,
        regional_context=_regional_context(region),
        scenario_output=scenario_output,
        analytics=analytics,
    )


def _format_tile_value(snapshot: MacroPulseRealtimeResponse, key: str) -> tuple[str, str]:
    indicator = next((item for item in snapshot.indicators if item.key == key), None)
    if not indicator:
        return ("Unavailable", "Waiting for source refresh")
    return (indicator.value, indicator.change)


async def build_dashboard_response(tenant_id: UUID) -> MacroPulseDashboardResponse:
    snapshot = await MacroPulseService().get_realtime_snapshot()
    rate_scenario = scenario_sim_tool("interest_rate", rate_delta_pct=0.5)
    fx_scenario = scenario_sim_tool("fx", fx_delta_pct=3.0)
    commodity_scenario = scenario_sim_tool("commodity", oil_delta_usd=5.0)
    combined_scenario = scenario_sim_tool("combined", rate_delta_pct=1.0, fx_delta_pct=4.0, oil_delta_usd=8.0)

    eurusd_value, eurusd_context = _format_tile_value(snapshot, "eurusd")
    ust_value, ust_context = _format_tile_value(snapshot, "ust10y")
    spread_value, spread_context = _format_tile_value(snapshot, "spread_2s10s")
    cpi_value, cpi_context = _format_tile_value(snapshot, "us_cpi")

    return MacroPulseDashboardResponse(
        tenant_id=tenant_id,
        generated_at=datetime.now(UTC),
        headline=snapshot.headline,
        kpi_tiles=[
            MacroPulseDashboardTile(key="eurusd", label="FX Monitor", value=eurusd_value, context=eurusd_context, tone="watch"),
            MacroPulseDashboardTile(key="ust10y", label="Rate Monitor", value=ust_value, context=ust_context, tone="action"),
            MacroPulseDashboardTile(key="spread_2s10s", label="Curve Signal", value=spread_value, context=spread_context, tone="watch"),
            MacroPulseDashboardTile(key="us_cpi", label="Inflation Print", value=cpi_value, context=cpi_context, tone="stable"),
        ],
        live_alerts=[
            MacroPulseDashboardAlert(
                severity="P2",
                title="Rate sensitivity drift",
                message=rate_scenario["headline"],
                confidence=88.0,
            ),
            MacroPulseDashboardAlert(
                severity="P2",
                title="FX hedge watch",
                message=fx_scenario["headline"],
                confidence=86.0,
            ),
            MacroPulseDashboardAlert(
                severity="P3",
                title="Commodity cost buffer",
                message=commodity_scenario["headline"],
                confidence=82.0,
            ),
        ],
        sensitivity_matrix=[
            MacroPulseSensitivityRow(
                scenario="interest_rate",
                impact_metric=rate_scenario["impact_metric"],
                impact_cr=rate_scenario["impact_cr"],
                confidence_low_cr=rate_scenario["confidence_interval_cr"]["low"],
                confidence_high_cr=rate_scenario["confidence_interval_cr"]["high"],
            ),
            MacroPulseSensitivityRow(
                scenario="fx",
                impact_metric=fx_scenario["impact_metric"],
                impact_cr=fx_scenario["impact_cr"],
                confidence_low_cr=fx_scenario["confidence_interval_cr"]["low"],
                confidence_high_cr=fx_scenario["confidence_interval_cr"]["high"],
            ),
            MacroPulseSensitivityRow(
                scenario="commodity",
                impact_metric=commodity_scenario["impact_metric"],
                impact_cr=commodity_scenario["impact_cr"],
                confidence_low_cr=commodity_scenario["confidence_interval_cr"]["low"],
                confidence_high_cr=commodity_scenario["confidence_interval_cr"]["high"],
            ),
            MacroPulseSensitivityRow(
                scenario="combined",
                impact_metric=combined_scenario["impact_metric"],
                impact_cr=combined_scenario["impact_cr"],
                confidence_low_cr=combined_scenario["confidence_interval_cr"]["low"],
                confidence_high_cr=combined_scenario["confidence_interval_cr"]["high"],
            ),
        ],
    )
