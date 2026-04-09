from __future__ import annotations


def get_metrics_summary() -> dict:
    """Compatibility shim for MacroPulse metrics until full tracing lands."""
    return {
        "latency_ms": {"p50": 0, "p95": 0, "p99": 0},
        "confidence": {"avg": 0.0, "min": 0.0, "max": 0.0},
        "runs": 0,
    }
