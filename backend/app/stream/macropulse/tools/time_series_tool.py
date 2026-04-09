from __future__ import annotations

from statistics import mean, pstdev

from app.core.ai_orchestration.tools.registry import tool_registry
from app.stream.macropulse.tool_schemas import TIME_SERIES_TOOL_SCHEMA


@tool_registry.register(
    name="time_series_tool",
    description="Compute rolling statistics, CAGR, momentum score, and slope for a macro KPI series",
    parameters_schema=TIME_SERIES_TOOL_SCHEMA,
)
def time_series_tool(values: list[float], label: str = "series") -> dict:
    if len(values) < 2:
        return {"label": label, "error": "Need at least 2 data points", "success": False}

    n = len(values)
    latest = values[-1]
    avg = mean(values)
    sigma = pstdev(values) if n >= 3 else 0.0

    # Rolling averages
    window_30 = values[-30:] if n >= 30 else values
    window_60 = values[-60:] if n >= 60 else values
    window_90 = values[-90:] if n >= 90 else values

    # CAGR (assumes each point = 1 period)
    first = values[0]
    cagr = ((latest / first) ** (1 / (n - 1)) - 1) * 100 if first != 0 else 0.0

    # Momentum: % change over last 5 periods
    momentum_base = values[-6] if n >= 6 else values[0]
    momentum_score = ((latest - momentum_base) / abs(momentum_base)) * 100 if momentum_base != 0 else 0.0

    # Slope (linear regression coefficient)
    x_mean = (n - 1) / 2
    numerator = sum((i - x_mean) * (v - avg) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0.0

    return {
        "label": label,
        "success": True,
        "n": n,
        "latest": round(latest, 4),
        "mean": round(avg, 4),
        "std_dev": round(sigma, 4),
        "rolling_avg_30": round(mean(window_30), 4),
        "rolling_avg_60": round(mean(window_60), 4),
        "rolling_avg_90": round(mean(window_90), 4),
        "cagr_pct": round(cagr, 3),
        "momentum_score_pct": round(momentum_score, 3),
        "slope": round(slope, 6),
        "trend": "up" if slope > 0 else "down" if slope < 0 else "flat",
    }
