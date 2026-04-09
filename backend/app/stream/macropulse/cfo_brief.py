from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel


class CFOBriefSection(BaseModel):
    title: str
    summary: str
    signal: str  # "positive" | "negative" | "neutral"
    confidence: float
    action: str


class CFOBriefResponse(BaseModel):
    tenant_id: str
    generated_at: datetime
    week_ending: str
    headline: str
    sections: list[CFOBriefSection]
    top3_scenarios: list[str]
    cfo_actions: list[str]
    overall_confidence: float


def build_cfo_brief(
    tenant_id: str,
    macro_context: dict[str, Any],
    cb_watch: dict[str, Any],
    fx_alert: dict[str, Any],
    commodity_tracker: dict[str, Any],
    sensitivity_update: dict[str, Any],
    top3_scenarios: list[str],
) -> CFOBriefResponse:
    """
    Deterministic LangChain-style RunnableChain for the weekly CFO Brief.
    Sections: macro_context → CB_watch → FX_alert → commodity_tracker → sensitivity_update → CFO_actions
    """
    now = datetime.now(UTC)
    week_ending = now.strftime("%d %b %Y")

    sections: list[CFOBriefSection] = []

    # 1. Macro Context
    sections.append(CFOBriefSection(
        title="Macro Environment",
        summary=macro_context.get("summary", "Global macro conditions remain in focus."),
        signal=macro_context.get("signal", "neutral"),
        confidence=macro_context.get("confidence", 0.85),
        action=macro_context.get("action", "Monitor macro dashboard weekly."),
    ))

    # 2. Central Bank Watch
    sections.append(CFOBriefSection(
        title="Central Bank Watch",
        summary=cb_watch.get("summary", "No major policy changes this week."),
        signal=cb_watch.get("signal", "neutral"),
        confidence=cb_watch.get("confidence", 0.88),
        action=cb_watch.get("action", "Review floating rate debt exposure."),
    ))

    # 3. FX Alert
    sections.append(CFOBriefSection(
        title="FX & Currency Risk",
        summary=fx_alert.get("summary", "FX volatility within acceptable range."),
        signal=fx_alert.get("signal", "neutral"),
        confidence=fx_alert.get("confidence", 0.82),
        action=fx_alert.get("action", "Verify hedge coverage ratio."),
    ))

    # 4. Commodity Tracker
    sections.append(CFOBriefSection(
        title="Commodity & Energy",
        summary=commodity_tracker.get("summary", "Commodity prices stable."),
        signal=commodity_tracker.get("signal", "neutral"),
        confidence=commodity_tracker.get("confidence", 0.80),
        action=commodity_tracker.get("action", "Review COGS sensitivity to oil price."),
    ))

    # 5. Sensitivity Update
    sections.append(CFOBriefSection(
        title="P&L Sensitivity Update",
        summary=sensitivity_update.get("summary", "Sensitivity models updated with latest inputs."),
        signal=sensitivity_update.get("signal", "neutral"),
        confidence=sensitivity_update.get("confidence", 0.87),
        action=sensitivity_update.get("action", "Share updated sensitivity matrix with treasury."),
    ))

    # Derive overall confidence
    overall_confidence = round(
        sum(s.confidence for s in sections) / len(sections), 2
    )

    # CFO actions aggregated
    cfo_actions = [s.action for s in sections if s.signal in ("negative", "neutral")]

    # Headline
    negative_sections = [s for s in sections if s.signal == "negative"]
    if negative_sections:
        headline = f"Action required: {negative_sections[0].title} signals elevated risk this week."
    else:
        headline = "Macro conditions are stable. Review sensitivity updates and maintain hedge positions."

    return CFOBriefResponse(
        tenant_id=tenant_id,
        generated_at=now,
        week_ending=week_ending,
        headline=headline,
        sections=sections,
        top3_scenarios=top3_scenarios,
        cfo_actions=cfo_actions,
        overall_confidence=overall_confidence,
    )
