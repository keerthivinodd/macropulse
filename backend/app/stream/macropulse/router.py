from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.core.gateway.realtime import realtime_hub
from app.stream.macropulse.ingestion.api.alert_engine import router as alerts_router
from app.stream.macropulse.ingestion.api.guardrails_runtime import router as guardrails_router
from app.stream.macropulse.ingestion.api.routes.hitl import router as ingestion_hitl_router
from app.stream.macropulse.ingestion.api.routes.tenant import router as ingestion_tenant_router
from app.stream.macropulse.auth_api import router as auth_router
from app.stream.macropulse.tenant_profile_api import router as tenant_router
from app.stream.macropulse.query_service import build_agent_query_response, build_dashboard_response
from app.stream.macropulse.schemas import (
    MacroPulseAgentQueryRequest,
    MacroPulseAgentQueryResponse,
    MacroPulseDashboardResponse,
    MacroPulseIngestionPlanResponse,
    MacroPulseRealtimeResponse,
    MacroPulseSourceCatalogResponse,
)
from app.stream.macropulse.source_registry import get_ingestion_plan, get_source_catalog
from app.stream.macropulse.service import MacroPulseService
from app.stream.macropulse.nl_query import NLQueryRequest, NLQueryResponse, parse_nl_query
from app.stream.macropulse.cfo_brief import CFOBriefResponse, build_cfo_brief
from app.stream.macropulse.cfo_brief_pipeline import run_cfo_brief_pipeline
from app.stream.macropulse.cost_routing import get_cost_router, classify_complexity
from app.stream.macropulse.event_publisher import get_event_publisher, get_event_schemas
from app.stream.macropulse.hitl import router as hitl_router, enqueue_for_hitl, should_route_to_hitl
from app.stream.macropulse.tracing import get_metrics_summary

router = APIRouter(prefix="/api/v1/macropulse", tags=["macropulse"])
router.include_router(auth_router)
router.include_router(tenant_router)
router.include_router(ingestion_tenant_router)
router.include_router(alerts_router)
router.include_router(ingestion_hitl_router)
router.include_router(guardrails_router)
router.include_router(hitl_router)


@router.get("/realtime", response_model=MacroPulseRealtimeResponse)
async def get_macropulse_realtime() -> MacroPulseRealtimeResponse:
    snapshot = await MacroPulseService().get_realtime_snapshot()
    await realtime_hub.publish(
        "macropulse.realtime",
        "snapshot.updated",
        snapshot.model_dump(mode="json"),
        sender="macropulse-service",
    )
    return snapshot


@router.get("/sources", response_model=MacroPulseSourceCatalogResponse)
async def get_macropulse_sources() -> MacroPulseSourceCatalogResponse:
    return get_source_catalog()


@router.get("/ingestion-plan", response_model=MacroPulseIngestionPlanResponse)
async def get_macropulse_ingestion_plan() -> MacroPulseIngestionPlanResponse:
    return get_ingestion_plan()


@router.post("/agent/query", response_model=MacroPulseAgentQueryResponse)
async def query_macropulse_agent(body: MacroPulseAgentQueryRequest) -> MacroPulseAgentQueryResponse:
    result = await build_agent_query_response(
        text=body.text,
        region=body.region,
        tenant_id=body.tenant_id,
    )
    # Auto-route low-confidence outputs to HITL queue
    if should_route_to_hitl(result.confidence, result.publish_status):
        enqueue_for_hitl(
            query=body.text,
            query_type=result.query_type,
            impact=result.impact,
            confidence=result.confidence,
            publish_status=result.publish_status,
            region=body.region,
            tenant_id=str(body.tenant_id) if body.tenant_id else None,
        )
    return result


@router.get("/dashboard/{tenant_id}", response_model=MacroPulseDashboardResponse)
async def get_macropulse_dashboard(tenant_id: UUID) -> MacroPulseDashboardResponse:
    return await build_dashboard_response(tenant_id)


@router.get("/metrics")
async def get_agent_metrics() -> dict:
    """Return p50/p95/p99 latency and confidence metrics for MacroPulse agent runs."""
    return get_metrics_summary()


@router.post("/nl-query", response_model=NLQueryResponse)
async def natural_language_query(body: NLQueryRequest) -> NLQueryResponse:
    """Parse a natural language macro question and route it to the correct engine."""
    return parse_nl_query(body)


@router.post("/cfo-brief", response_model=CFOBriefResponse)
async def generate_cfo_brief(
    tenant_id: str,
    macro_context: dict,
    cb_watch: dict,
    fx_alert: dict,
    commodity_tracker: dict,
    sensitivity_update: dict,
    top3_scenarios: list[str],
) -> CFOBriefResponse:
    """Generate the weekly CFO Brief via deterministic pipeline."""
    return build_cfo_brief(
        tenant_id=tenant_id,
        macro_context=macro_context,
        cb_watch=cb_watch,
        fx_alert=fx_alert,
        commodity_tracker=commodity_tracker,
        sensitivity_update=sensitivity_update,
        top3_scenarios=top3_scenarios,
    )


# ── Day 5 — Pipeline, Cost Routing, Pub/Sub (Pranisree) ─────

@router.post("/cfo-brief/pipeline")
async def run_cfo_pipeline(
    tenant_id: str = "tenant-india-001",
    upload_to_s3: bool = True,
    notify: bool = True,
    dry_run: bool = False,
) -> dict:
    """Run the full Monday CFO Brief pipeline end-to-end."""
    return await run_cfo_brief_pipeline(
        tenant_id=tenant_id,
        upload_to_s3=upload_to_s3,
        notify=notify,
        dry_run=dry_run,
    )


@router.get("/cost-routing/status")
async def get_cost_routing_status() -> dict:
    """Get LiteLLM cost routing budget status and summary."""
    router_instance = get_cost_router()
    return router_instance.get_cost_summary()


@router.post("/cost-routing/classify")
async def classify_query_complexity(query: str) -> dict:
    """Classify a query's complexity for cost-optimized routing."""
    complexity = classify_complexity(query)
    model = get_cost_router().select_model(query)
    return {
        "query": query,
        "complexity": complexity.value,
        "selected_model": model.model_id,
        "provider": model.provider,
        "input_cost_per_1k": model.input_cost_per_1k,
        "output_cost_per_1k": model.output_cost_per_1k,
    }


@router.get("/events/schemas")
async def get_pubsub_event_schemas() -> dict:
    """Return documented event schemas for all MacroPulse pub/sub channels."""
    return get_event_schemas()


@router.get("/events/log")
async def get_event_publish_log() -> dict:
    """Return recent pub/sub publish log."""
    publisher = await get_event_publisher()
    return {"events": publisher.get_publish_log()}
