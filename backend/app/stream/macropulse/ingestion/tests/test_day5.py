"""
Day 5 tests — Report export, cost routing, event publisher, CFO brief pipeline.
Run: pytest backend/app/stream/macropulse/ingestion/tests/test_day5.py -v
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. Report Export Tool — HTML generation with charts
# ---------------------------------------------------------------------------

def test_report_export_html_generates_valid_output():
    from app.stream.macropulse.tools.report_export_tool import report_export_tool

    result = report_export_tool(
        title="Weekly CFO Brief — 03 Apr 2026",
        summary="Macro conditions stable. Brent crude up 3.2% MoM.",
        format="html",
        upload_to_s3=False,
    )
    assert result["success"] is True
    assert result["format"] == "html"
    assert "rendered_html" in result
    assert "<html" in result["rendered_html"]
    assert "G-Sec" in result["rendered_html"] or "base64" in result["rendered_html"]
    assert result["export_status"] == "ready"


def test_report_export_pdf_generates_bytes():
    from app.stream.macropulse.tools.report_export_tool import report_export_tool

    result = report_export_tool(
        title="Weekly CFO Brief — 03 Apr 2026",
        summary="RBI held repo rate at 6.50%.",
        format="pdf",
        upload_to_s3=False,
    )
    assert result["success"] is True
    assert result["format"] == "pdf"
    assert "pdf_base64" in result
    assert result["pdf_size_bytes"] > 0
    assert result["export_status"] == "ready"


def test_report_export_html_with_brief_data():
    from app.stream.macropulse.tools.report_export_tool import report_export_tool

    brief_data = {
        "tenant_id": "tenant-india-001",
        "week_ending": "03 Apr 2026",
        "headline": "Macro conditions stable",
        "sections": [
            {"title": "Macro Environment", "summary": "Stable", "signal": "neutral", "confidence": 0.85, "action": "Monitor"},
            {"title": "FX Risk", "summary": "USD/INR at 83.45", "signal": "negative", "confidence": 0.78, "action": "Review hedge"},
        ],
        "top3_scenarios": ["Rate hike", "FX depreciation", "Oil spike"],
        "cfo_actions": ["Review hedge ratio", "Monitor CPI"],
        "overall_confidence": 0.84,
    }
    result = report_export_tool(
        title="Weekly CFO Brief",
        summary="Test",
        format="html",
        brief_data=brief_data,
        upload_to_s3=False,
    )
    assert result["success"] is True
    assert "Macro Environment" in result["rendered_html"]
    assert "FX Risk" in result["rendered_html"]


def test_report_export_with_chart_data():
    from app.stream.macropulse.tools.report_export_tool import report_export_tool

    result = report_export_tool(
        title="Brief with Charts",
        summary="Charts test",
        format="html",
        gsec_data=[{"date": "2026-03-28", "value": 7.18}, {"date": "2026-04-02", "value": 7.22}],
        fx_data=[{"pair": "USD/INR", "change_pct": 0.35}],
        commodity_data=[{"name": "Brent Crude", "mom_pct": 3.2}],
        upload_to_s3=False,
    )
    assert result["success"] is True
    # Charts embedded as base64 PNG
    assert "data:image/png;base64," in result["rendered_html"]


def test_report_export_unsupported_format():
    from app.stream.macropulse.tools.report_export_tool import report_export_tool

    result = report_export_tool(title="Test", summary="Test", format="csv", upload_to_s3=False)
    assert result["success"] is False
    assert result["export_status"] == "unsupported_format"


# ---------------------------------------------------------------------------
# 2. Chart generation (matplotlib)
# ---------------------------------------------------------------------------

def test_gsec_chart_generates_png():
    from app.stream.macropulse.tools.report_export_tool import _generate_gsec_yield_chart
    png_bytes = _generate_gsec_yield_chart([])
    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 1000  # Valid PNG should be > 1KB
    assert png_bytes[:4] == b"\x89PNG"  # PNG magic bytes


def test_fx_chart_generates_png():
    from app.stream.macropulse.tools.report_export_tool import _generate_fx_7d_chart
    png_bytes = _generate_fx_7d_chart([{"pair": "USD/INR", "change_pct": 0.5}])
    assert isinstance(png_bytes, bytes)
    assert png_bytes[:4] == b"\x89PNG"


def test_commodity_chart_generates_png():
    from app.stream.macropulse.tools.report_export_tool import _generate_commodity_mom_chart
    png_bytes = _generate_commodity_mom_chart([{"name": "Brent", "mom_pct": 3.2}])
    assert isinstance(png_bytes, bytes)
    assert png_bytes[:4] == b"\x89PNG"


# ---------------------------------------------------------------------------
# 3. LiteLLM Cost Routing — complexity classification
# ---------------------------------------------------------------------------

def test_classify_high_complexity():
    from app.stream.macropulse.cost_routing import classify_complexity, QueryComplexity
    assert classify_complexity("Run combined scenario for rate and FX impact on EBITDA") == QueryComplexity.HIGH


def test_classify_medium_complexity():
    from app.stream.macropulse.cost_routing import classify_complexity, QueryComplexity
    assert classify_complexity("What is the current CPI trend?") == QueryComplexity.MEDIUM


def test_classify_low_complexity():
    from app.stream.macropulse.cost_routing import classify_complexity, QueryComplexity
    assert classify_complexity("Hello, how are you?") == QueryComplexity.LOW


# ---------------------------------------------------------------------------
# 4. Cost Router — model selection & budget enforcement
# ---------------------------------------------------------------------------

def test_cost_router_selects_gpt4o_for_high_complexity():
    from app.stream.macropulse.cost_routing import LiteLLMCostRouter
    router = LiteLLMCostRouter(daily_budget_usd=50.0)
    model = router.select_model("Run combined stress test on rate and FX exposure")
    assert model.model_id == "gpt-4o"


def test_cost_router_selects_gpt35_for_medium():
    from app.stream.macropulse.cost_routing import LiteLLMCostRouter
    router = LiteLLMCostRouter(daily_budget_usd=50.0)
    model = router.select_model("What is the repo rate trend?")
    assert model.model_id == "gpt-3.5-turbo"


def test_cost_router_selects_local_for_low():
    from app.stream.macropulse.cost_routing import LiteLLMCostRouter
    router = LiteLLMCostRouter(daily_budget_usd=50.0)
    model = router.select_model("Hi there")
    assert model.model_id == "llama3"


def test_cost_router_forces_local_when_budget_exceeded():
    from app.stream.macropulse.cost_routing import LiteLLMCostRouter
    router = LiteLLMCostRouter(daily_budget_usd=0.001)
    # Record enough usage to exceed budget
    router.record_usage("gpt-4o", 10000, 5000)
    model = router.select_model("Run complex combined scenario analysis")
    assert model.model_id == "llama3"


def test_cost_router_records_usage_correctly():
    from app.stream.macropulse.cost_routing import LiteLLMCostRouter
    router = LiteLLMCostRouter()
    record = router.record_usage("gpt-4o", 1000, 500)
    assert record.cost_usd > 0
    assert record.input_tokens == 1000
    assert record.output_tokens == 500


def test_cost_router_budget_status():
    from app.stream.macropulse.cost_routing import LiteLLMCostRouter
    router = LiteLLMCostRouter(daily_budget_usd=10.0)
    router.record_usage("gpt-4o", 1000, 500)
    status = router.get_budget_status()
    assert status["daily_budget_usd"] == 10.0
    assert status["current_spend_usd"] > 0
    assert status["budget_exceeded"] is False


def test_cost_router_summary():
    from app.stream.macropulse.cost_routing import LiteLLMCostRouter
    router = LiteLLMCostRouter()
    router.record_usage("gpt-4o", 1000, 500)
    router.record_usage("gpt-3.5-turbo", 2000, 1000)
    summary = router.get_cost_summary()
    assert summary["total_requests"] == 2
    assert "gpt-4o" in summary["by_model"]
    assert "gpt-3.5-turbo" in summary["by_model"]


# ---------------------------------------------------------------------------
# 5. Redis Pub/Sub — Event schemas validation
# ---------------------------------------------------------------------------

def test_currency_signal_event_schema():
    from app.stream.macropulse.event_publisher import CurrencySignalEvent
    event = CurrencySignalEvent(
        tenant_id="tenant-india-001",
        currency_pair="USD/INR",
        signal_type="depreciation",
        magnitude_pct=1.25,
        direction="up",
        confidence=0.88,
    )
    assert event.event_type == "currency_signal"
    assert event.channel == "macro.currency_signal"
    payload = json.loads(event.model_dump_json())
    assert "event_id" in payload
    assert payload["currency_pair"] == "USD/INR"


def test_slowdown_risk_event_schema():
    from app.stream.macropulse.event_publisher import SlowdownRiskEvent
    event = SlowdownRiskEvent(
        tenant_id="tenant-india-001",
        risk_level="high",
        risk_score=72.5,
        confidence=0.82,
        indicators=["gdp_decline", "inflation_rising"],
        affected_regions=["India"],
    )
    assert event.event_type == "slowdown_risk"
    assert event.channel == "macro.slowdown_risk"
    assert event.risk_score == 72.5


def test_commodity_inflation_event_schema():
    from app.stream.macropulse.event_publisher import CommodityInflationEvent
    event = CommodityInflationEvent(
        tenant_id="tenant-india-001",
        commodity="brent_crude",
        price_change_pct=3.2,
        direction="up",
        confidence=0.85,
        current_price_usd=82.50,
    )
    assert event.event_type == "commodity_inflation"
    assert event.channel == "macro.commodity_inflation"
    assert event.current_price_usd == 82.50


def test_event_schema_documentation():
    from app.stream.macropulse.event_publisher import get_event_schemas
    schemas = get_event_schemas()
    assert "channels" in schemas
    assert "macro.currency_signal" in schemas["channels"]
    assert "macro.slowdown_risk" in schemas["channels"]
    assert "macro.commodity_inflation" in schemas["channels"]
    assert schemas["channels"]["macro.currency_signal"]["consumer"] == "GeoRisk"
    assert schemas["channels"]["macro.slowdown_risk"]["consumer"] == "ChurnGuard"
    assert schemas["channels"]["macro.commodity_inflation"]["consumer"] == "SLAMonitor"


# ---------------------------------------------------------------------------
# 6. Redis Pub/Sub — Publisher integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_event_publisher_publishes_currency_signal():
    from app.stream.macropulse.event_publisher import MacroPulseEventPublisher

    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock(return_value=2)
    publisher = MacroPulseEventPublisher(redis_client=mock_redis)

    result = await publisher.publish_currency_signal(
        tenant_id="tenant-india-001",
        currency_pair="USD/INR",
        signal_type="depreciation",
        magnitude_pct=1.25,
        direction="up",
        confidence=0.88,
    )
    assert result["success"] is True
    assert result["channel"] == "macro.currency_signal"
    assert result["consumer"] == "GeoRisk"
    assert result["subscriber_count"] == 2
    mock_redis.publish.assert_called_once()


@pytest.mark.asyncio
async def test_event_publisher_publishes_slowdown_risk():
    from app.stream.macropulse.event_publisher import MacroPulseEventPublisher

    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock(return_value=1)
    publisher = MacroPulseEventPublisher(redis_client=mock_redis)

    result = await publisher.publish_slowdown_risk(
        tenant_id="tenant-india-001",
        risk_level="high",
        risk_score=72.5,
        confidence=0.82,
    )
    assert result["success"] is True
    assert result["channel"] == "macro.slowdown_risk"
    assert result["consumer"] == "ChurnGuard"


@pytest.mark.asyncio
async def test_event_publisher_publishes_commodity_inflation():
    from app.stream.macropulse.event_publisher import MacroPulseEventPublisher

    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock(return_value=1)
    publisher = MacroPulseEventPublisher(redis_client=mock_redis)

    result = await publisher.publish_commodity_inflation(
        tenant_id="tenant-india-001",
        commodity="brent_crude",
        price_change_pct=3.2,
        direction="up",
        confidence=0.85,
    )
    assert result["success"] is True
    assert result["channel"] == "macro.commodity_inflation"
    assert result["consumer"] == "SLAMonitor"


@pytest.mark.asyncio
async def test_event_publisher_handles_redis_failure():
    from app.stream.macropulse.event_publisher import MacroPulseEventPublisher, CurrencySignalEvent

    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock(side_effect=ConnectionError("Redis down"))
    publisher = MacroPulseEventPublisher(redis_client=mock_redis)

    result = await publisher.publish_currency_signal(
        tenant_id="test",
        currency_pair="USD/INR",
        signal_type="depreciation",
        magnitude_pct=1.0,
        direction="up",
        confidence=0.8,
    )
    assert result["success"] is False
    assert "error" in result


# ---------------------------------------------------------------------------
# 7. CFO Brief Pipeline — dry run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cfo_brief_pipeline_dry_run():
    from app.stream.macropulse.cfo_brief_pipeline import run_cfo_brief_pipeline

    result = await run_cfo_brief_pipeline(
        tenant_id="tenant-india-001",
        upload_to_s3=False,
        notify=False,
        dry_run=True,
    )
    assert result["steps_completed"] == 7
    assert result["steps_total"] == 7
    assert result["confidence_score"] == 100.0
    assert result["publish_status"] == "publish"
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_cfo_brief_pipeline_generates_pdf():
    from app.stream.macropulse.cfo_brief_pipeline import run_cfo_brief_pipeline

    result = await run_cfo_brief_pipeline(
        tenant_id="tenant-india-001",
        upload_to_s3=False,
        notify=False,
        dry_run=True,
    )
    # PDF export step should complete
    pdf_step = next((s for s in result["steps"] if s["step"] == "6_pdf_html_export"), None)
    assert pdf_step is not None
    assert pdf_step["status"] == "completed"
    assert pdf_step["pdf_success"] is True
    assert pdf_step["pdf_size_bytes"] > 0


@pytest.mark.asyncio
async def test_cfo_brief_pipeline_total_duration_under_30s():
    """Pipeline should complete in under 30 seconds (dry run)."""
    from app.stream.macropulse.cfo_brief_pipeline import run_cfo_brief_pipeline

    result = await run_cfo_brief_pipeline(
        tenant_id="tenant-india-001",
        upload_to_s3=False,
        notify=False,
        dry_run=True,
    )
    assert result["total_duration_ms"] < 30_000, (
        f"Pipeline took {result['total_duration_ms']}ms — exceeds 30s target"
    )
