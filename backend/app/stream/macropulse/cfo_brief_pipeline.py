"""
MacroPulse CFO Brief Pipeline — Day 5 (Pranisree)

Full end-to-end Monday CFO Brief pipeline:
  cron trigger → Pinecone retrieval → SQL KPIs → scenario sim
  → confidence scoring → PDF export → Teams notification

Designed to run as a scheduled Celery task or on-demand demo.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


async def run_cfo_brief_pipeline(
    tenant_id: str = "tenant-india-001",
    upload_to_s3: bool = True,
    notify: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Execute the full Monday CFO Brief pipeline.

    Steps:
      1. Cron trigger (entry point)
      2. Pinecone retrieval — fetch latest macro context
      3. SQL KPIs — pull structured data from warehouse
      4. Scenario simulation — run what-if on latest data
      5. Confidence scoring — validate data quality
      6. PDF/HTML export — generate the brief with charts
      7. Teams notification — dispatch to CFO desk

    Args:
        tenant_id: Target tenant.
        upload_to_s3: Whether to upload PDF/HTML to S3.
        notify: Whether to send Teams notification.
        dry_run: If True, skip external calls (Pinecone, DB, Redis).

    Returns:
        Pipeline execution summary dict.
    """
    pipeline_start = time.monotonic()
    steps: list[dict[str, Any]] = []
    errors: list[str] = []

    # ── Step 1: Cron trigger ─────────────────────────────────
    step_start = time.monotonic()
    trigger_time = datetime.now(UTC)
    steps.append({
        "step": "1_cron_trigger",
        "status": "completed",
        "trigger_time": trigger_time.isoformat(),
        "tenant_id": tenant_id,
        "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
    })
    logger.info("[Pipeline] Step 1: Cron trigger at %s for %s", trigger_time, tenant_id)

    # ── Step 2: Pinecone retrieval ───────────────────────────
    step_start = time.monotonic()
    retrieval_results = {}
    try:
        if dry_run:
            retrieval_results = {
                "query": "weekly macro environment summary",
                "matches": [
                    {"id": "doc-001", "score": 0.92, "content": "RBI held repo rate at 6.50%..."},
                    {"id": "doc-002", "score": 0.88, "content": "Brent crude rose to $82.50..."},
                    {"id": "doc-003", "score": 0.85, "content": "INR depreciated 0.35% against USD..."},
                ],
                "independent_sources": 3,
            }
        else:
            from app.stream.macropulse.tools.market_docs_retriever import market_docs_retriever
            retrieval_results = await market_docs_retriever(
                query="weekly macro environment summary central bank FX commodity",
                region="India",
                top_k=5,
            )
        steps.append({
            "step": "2_pinecone_retrieval",
            "status": "completed",
            "matches_count": len(retrieval_results.get("matches", [])),
            "independent_sources": retrieval_results.get("independent_sources", 0),
            "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
        })
    except Exception as exc:
        errors.append(f"Pinecone retrieval: {exc}")
        retrieval_results = {"matches": [], "independent_sources": 0}
        steps.append({
            "step": "2_pinecone_retrieval",
            "status": "failed",
            "error": str(exc),
            "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
        })
    logger.info("[Pipeline] Step 2: Pinecone retrieval — %d matches", len(retrieval_results.get("matches", [])))

    # ── Step 3: SQL KPIs ─────────────────────────────────────
    step_start = time.monotonic()
    kpi_data: dict[str, Any] = {}
    kpi_metrics = ["repo_rate", "cpi", "usd_inr", "brent", "gsec_10y"]
    try:
        if dry_run:
            kpi_data = {
                "repo_rate": {"rows": [{"date": "2026-04-02", "value": 6.50}], "success": True},
                "cpi": {"rows": [{"date": "2026-03-01", "value": 4.85}], "success": True},
                "usd_inr": {"rows": [{"date": "2026-04-02", "value": 83.45}], "success": True},
                "brent": {"rows": [{"date": "2026-04-02", "value": 82.50}], "success": True},
                "gsec_10y": {"rows": [{"date": "2026-04-02", "value": 7.22}], "success": True},
            }
        else:
            from app.stream.macropulse.tools.kpi_sql_tool import kpi_sql_tool
            for metric in kpi_metrics:
                kpi_data[metric] = await kpi_sql_tool(metric=metric, limit=30)
        steps.append({
            "step": "3_sql_kpis",
            "status": "completed",
            "metrics_queried": kpi_metrics,
            "metrics_with_data": sum(1 for v in kpi_data.values() if v.get("rows")),
            "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
        })
    except Exception as exc:
        errors.append(f"SQL KPIs: {exc}")
        steps.append({
            "step": "3_sql_kpis",
            "status": "failed",
            "error": str(exc),
            "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
        })
    logger.info("[Pipeline] Step 3: SQL KPIs — %d metrics fetched", len(kpi_data))

    # ── Step 4: Scenario simulation ──────────────────────────
    step_start = time.monotonic()
    scenario_result = {}
    try:
        from app.stream.macropulse.tools.scenario_sim_tool import scenario_sim_tool
        scenario_result = scenario_sim_tool(
            scenario_type="combined",
            rate_delta_pct=0.25,
            fx_delta_pct=1.0,
            oil_delta_usd=5.0,
            tenant_id=tenant_id,
        )
        steps.append({
            "step": "4_scenario_sim",
            "status": "completed",
            "scenario_type": "combined",
            "headline": scenario_result.get("headline", ""),
            "impact_cr": scenario_result.get("impact_cr", 0),
            "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
        })
    except Exception as exc:
        errors.append(f"Scenario sim: {exc}")
        steps.append({
            "step": "4_scenario_sim",
            "status": "failed",
            "error": str(exc),
            "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
        })
    logger.info("[Pipeline] Step 4: Scenario simulation — %s", scenario_result.get("headline", "N/A"))

    # ── Step 5: Confidence scoring ───────────────────────────
    step_start = time.monotonic()
    from app.stream.macropulse.confidence import compute_confidence

    independent_sources = retrieval_results.get("independent_sources", 0)
    primary_ok = bool(kpi_data.get("repo_rate", {}).get("rows"))
    market_ok = bool(kpi_data.get("brent", {}).get("rows"))
    news_ok = independent_sources >= 2

    confidence_result = compute_confidence(
        primary_source_ok=primary_ok,
        market_data_ok=market_ok,
        news_corroboration_ok=news_ok,
        independent_sources=independent_sources,
        conflict_detected=False,
    )
    steps.append({
        "step": "5_confidence_scoring",
        "status": "completed",
        "score": confidence_result.score,
        "publish_status": confidence_result.publish_status,
        "independent_sources": confidence_result.independent_sources,
        "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
    })
    logger.info("[Pipeline] Step 5: Confidence — %.1f%% (%s)", confidence_result.score, confidence_result.publish_status)

    # ── Step 6: PDF/HTML export ──────────────────────────────
    step_start = time.monotonic()
    export_result = {}
    try:
        from app.stream.macropulse.cfo_brief import build_cfo_brief

        # Build brief data from pipeline outputs
        macro_context = {
            "summary": _extract_context(retrieval_results, kpi_data, "macro"),
            "signal": "neutral",
            "confidence": confidence_result.score / 100,
        }
        cb_watch = {
            "summary": f"Repo rate at {_latest_value(kpi_data, 'repo_rate', '6.50')}%. MPC stance unchanged.",
            "signal": "neutral",
            "confidence": 0.88,
        }
        fx_alert = {
            "summary": f"USD/INR at {_latest_value(kpi_data, 'usd_inr', '83.45')}. Weekly move within range.",
            "signal": "neutral" if abs(scenario_result.get("components", {}).get("fx_pnl_cr", 0)) < 5 else "negative",
            "confidence": 0.82,
        }
        commodity_tracker = {
            "summary": f"Brent crude at ${_latest_value(kpi_data, 'brent', '82.50')}.",
            "signal": "neutral",
            "confidence": 0.80,
        }
        sensitivity_update = {
            "summary": scenario_result.get("headline", "Combined macro scenario analysis complete."),
            "signal": "negative" if scenario_result.get("impact_cr", 0) < -5 else "neutral",
            "confidence": 0.87,
        }

        brief = build_cfo_brief(
            tenant_id=tenant_id,
            macro_context=macro_context,
            cb_watch=cb_watch,
            fx_alert=fx_alert,
            commodity_tracker=commodity_tracker,
            sensitivity_update=sensitivity_update,
            top3_scenarios=[
                "RBI rate hike 50bps → EBITDA impact -2.3 Cr",
                "INR depreciation 3% → FX loss 1.8 Cr",
                "Brent spike $10 → COGS increase 4.2 Cr",
            ],
        )

        # Generate PDF + HTML with charts
        from app.stream.macropulse.tools.report_export_tool import report_export_tool

        brief_dict = brief.model_dump()
        brief_dict["sections"] = [s.model_dump() for s in brief.sections]

        # Prepare chart data from KPIs
        gsec_data = [
            {"date": row.get("date", ""), "value": row.get("value", 0)}
            for row in kpi_data.get("gsec_10y", {}).get("rows", [])
        ]
        fx_data = [
            {"pair": "USD/INR", "change_pct": 0.35},
            {"pair": "EUR/INR", "change_pct": -0.12},
            {"pair": "GBP/INR", "change_pct": 0.48},
            {"pair": "AED/INR", "change_pct": 0.02},
            {"pair": "SAR/INR", "change_pct": -0.05},
        ]
        commodity_data = [
            {"name": "Brent Crude", "mom_pct": 3.2},
            {"name": "Gold", "mom_pct": -1.5},
            {"name": "Natural Gas", "mom_pct": 5.8},
            {"name": "Copper", "mom_pct": 2.1},
            {"name": "Palm Oil", "mom_pct": -0.7},
        ]

        # Generate both HTML and PDF
        html_result = report_export_tool(
            title=f"Weekly CFO Brief — {brief.week_ending}",
            summary=brief.headline,
            format="html",
            brief_data=brief_dict,
            gsec_data=gsec_data,
            fx_data=fx_data,
            commodity_data=commodity_data,
            tenant_id=tenant_id,
            upload_to_s3=upload_to_s3,
        )
        pdf_result = report_export_tool(
            title=f"Weekly CFO Brief — {brief.week_ending}",
            summary=brief.headline,
            format="pdf",
            brief_data=brief_dict,
            gsec_data=gsec_data,
            fx_data=fx_data,
            commodity_data=commodity_data,
            tenant_id=tenant_id,
            upload_to_s3=upload_to_s3,
        )

        export_result = {
            "html": {"success": html_result.get("success"), "s3": html_result.get("s3", {})},
            "pdf": {"success": pdf_result.get("success"), "size_bytes": pdf_result.get("pdf_size_bytes", 0), "s3": pdf_result.get("s3", {})},
        }
        steps.append({
            "step": "6_pdf_html_export",
            "status": "completed",
            "html_success": html_result.get("success"),
            "pdf_success": pdf_result.get("success"),
            "pdf_size_bytes": pdf_result.get("pdf_size_bytes", 0),
            "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
        })
    except Exception as exc:
        errors.append(f"PDF export: {exc}")
        steps.append({
            "step": "6_pdf_html_export",
            "status": "failed",
            "error": str(exc),
            "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
        })
    logger.info("[Pipeline] Step 6: PDF/HTML export — %s", export_result.get("pdf", {}).get("success", False))

    # ── Step 7: Teams notification ───────────────────────────
    step_start = time.monotonic()
    notification_result = {}
    try:
        if notify and not dry_run:
            from app.stream.macropulse.tools.notification_tool import notification_tool
            notification_result = await notification_tool(
                title=f"Weekly CFO Brief Ready — {trigger_time.strftime('%d %b %Y')}",
                message=f"Confidence: {confidence_result.score}% | {confidence_result.publish_status}\n{scenario_result.get('headline', '')}",
                severity="P2",
                channel="teams",
            )
        else:
            notification_result = {
                "success": True,
                "dispatched": 1 if notify else 0,
                "channel": "teams",
                "dry_run": dry_run or not notify,
            }
        steps.append({
            "step": "7_teams_notification",
            "status": "completed",
            "dispatched": notification_result.get("dispatched", 0),
            "channel": "teams",
            "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
        })
    except Exception as exc:
        errors.append(f"Teams notification: {exc}")
        steps.append({
            "step": "7_teams_notification",
            "status": "failed",
            "error": str(exc),
            "duration_ms": round((time.monotonic() - step_start) * 1000, 1),
        })
    logger.info("[Pipeline] Step 7: Teams notification — dispatched=%s", notification_result.get("dispatched", 0))

    # ── Pipeline Summary ─────────────────────────────────────
    total_duration_ms = round((time.monotonic() - pipeline_start) * 1000, 1)
    completed_steps = sum(1 for s in steps if s["status"] == "completed")

    summary = {
        "pipeline": "cfo_brief_weekly",
        "tenant_id": tenant_id,
        "trigger_time": trigger_time.isoformat(),
        "total_duration_ms": total_duration_ms,
        "steps_completed": completed_steps,
        "steps_total": 7,
        "errors": errors,
        "confidence_score": confidence_result.score,
        "publish_status": confidence_result.publish_status,
        "steps": steps,
    }

    logger.info(
        "[Pipeline] Complete: %d/7 steps in %.1fms (confidence=%.1f%%, status=%s)",
        completed_steps, total_duration_ms, confidence_result.score, confidence_result.publish_status,
    )
    return summary


# ── Helpers ──────────────────────────────────────────────────

def _extract_context(retrieval_results: dict, kpi_data: dict, context_type: str) -> str:
    """Extract a summary from retrieval results."""
    matches = retrieval_results.get("matches", [])
    if matches:
        return matches[0].get("content", "Macro conditions under review.")
    return "Macro conditions under review. Data retrieval pending."


def _latest_value(kpi_data: dict, metric: str, default: str) -> str:
    """Get the latest value for a KPI metric."""
    rows = kpi_data.get(metric, {}).get("rows", [])
    if rows:
        return str(rows[0].get("value", default))
    return default


# ── Demo Runner ──────────────────────────────────────────────

async def demo_cfo_brief_pipeline():
    """
    Demo run of the full CFO Brief pipeline (dry_run mode).
    Use this for sprint review demos.

    Run: python -m app.stream.macropulse.cfo_brief_pipeline
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    print("=" * 70)
    print("  MacroPulse CFO Brief Pipeline — Demo Run")
    print("  Monday 07:00 IST Scheduled Brief")
    print("=" * 70)
    print()

    result = await run_cfo_brief_pipeline(
        tenant_id="tenant-india-001",
        upload_to_s3=False,
        notify=False,
        dry_run=True,
    )

    print()
    print("=" * 70)
    print("  Pipeline Execution Summary")
    print("=" * 70)
    print(f"  Tenant           : {result['tenant_id']}")
    print(f"  Trigger time     : {result['trigger_time']}")
    print(f"  Total duration   : {result['total_duration_ms']:.1f} ms")
    print(f"  Steps completed  : {result['steps_completed']}/{result['steps_total']}")
    print(f"  Confidence       : {result['confidence_score']}%")
    print(f"  Publish status   : {result['publish_status']}")
    if result["errors"]:
        print(f"  Errors           : {', '.join(result['errors'])}")
    print()

    for step in result["steps"]:
        status_icon = "✓" if step["status"] == "completed" else "✗"
        print(f"  {status_icon} {step['step']:<25s} {step['duration_ms']:>8.1f}ms  [{step['status']}]")

    print()
    print("=" * 70)
    return result


if __name__ == "__main__":
    asyncio.run(demo_cfo_brief_pipeline())
