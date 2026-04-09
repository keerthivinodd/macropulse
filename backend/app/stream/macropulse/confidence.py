from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfidenceBreakdown:
    score: float
    independent_sources: int
    conflict_detected: bool
    publish_status: str


def compute_confidence(
    primary_source_ok: bool,
    market_data_ok: bool,
    news_corroboration_ok: bool,
    independent_sources: int,
    conflict_detected: bool = False,
) -> ConfidenceBreakdown:
    score = 0.0
    score += 40.0 if primary_source_ok else 0.0
    score += 35.0 if market_data_ok else 0.0
    score += 25.0 if news_corroboration_ok else 0.0

    if conflict_detected:
        score = max(0.0, score - 15.0)

    if score >= 85.0:
        publish_status = "publish"
    elif score >= 70.0:
        publish_status = "review"
    else:
        publish_status = "hitl_queue"

    return ConfidenceBreakdown(
        score=round(score, 1),
        independent_sources=independent_sources,
        conflict_detected=conflict_detected,
        publish_status=publish_status,
    )
