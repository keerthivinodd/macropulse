from __future__ import annotations

from app.core.ai_orchestration.tools.registry import tool_registry
from app.stream.macropulse.anomaly import z_score_flags
from app.stream.macropulse.tool_schemas import ANOMALY_DETECTOR_SCHEMA


@tool_registry.register(
    name="anomaly_detector",
    description="Run MacroPulse anomaly detection over KPI series using simple z-score thresholds",
    parameters_schema=ANOMALY_DETECTOR_SCHEMA,
)
def anomaly_detector(values: list[float]) -> dict:
    result = z_score_flags(values)
    severity_map = {
        "critical": "P1",
        "watch": "P2",
        "normal": "P3",
        "stable": "P3",
        "insufficient_data": "info",
    }
    return {
        "input_points": len(values),
        "status": result["status"],
        "z_score": result["z_score"],
        "alert_classification": severity_map.get(result["status"], "info"),
    }
