"""
MacroPulse LiteLLM Cost Routing — Day 5 (Pranisree)

Fallback chain: GPT-4o → GPT-3.5-turbo → local model
Routes based on query complexity. Budget cap alert if cost > threshold.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Models ───────────────────────────────────────────────────

class QueryComplexity(str, Enum):
    HIGH = "high"       # Multi-variable scenarios, combined impact analysis
    MEDIUM = "medium"   # Single-variable queries, KPI lookups
    LOW = "low"         # Simple factual, source queries, greetings


@dataclass
class ModelTier:
    model_id: str
    provider: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    max_context: int
    priority: int  # lower = higher priority within tier


@dataclass
class CostRecord:
    model_id: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: datetime
    tenant_id: str | None = None
    query_complexity: str = "medium"


@dataclass
class BudgetAlert:
    tenant_id: str
    current_spend_usd: float
    budget_limit_usd: float
    alert_type: str  # "warning" (80%) or "exceeded"
    timestamp: datetime


# ── Fallback Chain Configuration ─────────────────────────────

# GPT-4o → GPT-3.5-turbo → local model
FALLBACK_CHAIN: list[ModelTier] = [
    ModelTier(
        model_id="gpt-4o",
        provider="openai",
        input_cost_per_1k=0.0025,
        output_cost_per_1k=0.01,
        max_context=128_000,
        priority=0,
    ),
    ModelTier(
        model_id="gpt-3.5-turbo",
        provider="openai",
        input_cost_per_1k=0.0005,
        output_cost_per_1k=0.0015,
        max_context=16_385,
        priority=1,
    ),
    ModelTier(
        model_id="llama3",
        provider="local",
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
        max_context=8_192,
        priority=2,
    ),
]

# Complexity → allowed model tiers (by priority ceiling)
COMPLEXITY_ROUTING: dict[QueryComplexity, int] = {
    QueryComplexity.HIGH: 0,    # Start from GPT-4o
    QueryComplexity.MEDIUM: 1,  # Start from GPT-3.5-turbo
    QueryComplexity.LOW: 2,     # Start from local model
}


# ── Complexity Classifier ────────────────────────────────────

HIGH_COMPLEXITY_KEYWORDS = [
    "combined", "multi", "scenario", "ebitda", "sensitivity", "hedge",
    "strategy", "simulate", "stress test", "what-if", "projection",
    "forecast", "correlation", "portfolio",
]
MEDIUM_COMPLEXITY_KEYWORDS = [
    "impact", "rate", "price", "trend", "compare", "change", "yield",
    "exposure", "risk", "volatility", "inflation", "cpi", "gdp",
]


def classify_complexity(query: str) -> QueryComplexity:
    """Classify NL query complexity for cost-optimized routing."""
    lower = query.lower()

    # Multi-variable or compound queries are HIGH
    variable_count = sum(
        1 for kw in ["rate", "fx", "oil", "commodity", "currency", "inflation"]
        if kw in lower
    )
    if variable_count >= 2:
        return QueryComplexity.HIGH

    if any(kw in lower for kw in HIGH_COMPLEXITY_KEYWORDS):
        return QueryComplexity.HIGH

    if any(kw in lower for kw in MEDIUM_COMPLEXITY_KEYWORDS):
        return QueryComplexity.MEDIUM

    return QueryComplexity.LOW


# ── Cost Router ──────────────────────────────────────────────

class LiteLLMCostRouter:
    """
    Routes NL queries to the most cost-effective model based on complexity.
    Implements fallback chain with budget cap alerts.
    """

    def __init__(
        self,
        fallback_chain: list[ModelTier] | None = None,
        daily_budget_usd: float = 50.0,
        warning_threshold_pct: float = 0.80,
    ):
        self._chain = fallback_chain or FALLBACK_CHAIN
        self._daily_budget_usd = daily_budget_usd
        self._warning_threshold_pct = warning_threshold_pct
        self._cost_records: list[CostRecord] = []
        self._alerts: list[BudgetAlert] = []
        self._daily_spend: dict[str, float] = {}  # date_str → total USD

    def select_model(self, query: str, tenant_id: str | None = None) -> ModelTier:
        """Select the optimal model based on query complexity and budget."""
        complexity = classify_complexity(query)
        start_priority = COMPLEXITY_ROUTING[complexity]

        # Check budget — if near limit, downgrade to cheaper model
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current_spend = self._daily_spend.get(today, 0.0)

        if current_spend >= self._daily_budget_usd:
            # Budget exceeded — force local model
            logger.warning("Daily budget exceeded ($%.2f/$%.2f). Forcing local model.",
                          current_spend, self._daily_budget_usd)
            self._emit_alert(tenant_id or "global", current_spend, "exceeded")
            return self._chain[-1]  # local model

        if current_spend >= self._daily_budget_usd * self._warning_threshold_pct:
            # Near budget — downgrade one tier
            logger.warning("Approaching budget limit ($%.2f/$%.2f). Downgrading model tier.",
                          current_spend, self._daily_budget_usd)
            self._emit_alert(tenant_id or "global", current_spend, "warning")
            start_priority = min(start_priority + 1, len(self._chain) - 1)

        # Return the model at the selected priority
        for tier in self._chain:
            if tier.priority >= start_priority:
                return tier

        return self._chain[-1]

    def record_usage(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        tenant_id: str | None = None,
        query_complexity: str = "medium",
    ) -> CostRecord:
        """Record token usage and compute cost."""
        tier = next((t for t in self._chain if t.model_id == model_id), None)
        if tier:
            cost = (input_tokens / 1000 * tier.input_cost_per_1k +
                    output_tokens / 1000 * tier.output_cost_per_1k)
        else:
            cost = 0.0

        record = CostRecord(
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost, 6),
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            query_complexity=query_complexity,
        )
        self._cost_records.append(record)

        # Update daily spend
        today = record.timestamp.strftime("%Y-%m-%d")
        self._daily_spend[today] = self._daily_spend.get(today, 0.0) + cost

        return record

    def get_daily_spend(self, date_str: str | None = None) -> float:
        """Get total spend for a given day."""
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return round(self._daily_spend.get(date_str, 0.0), 4)

    def get_budget_status(self) -> dict[str, Any]:
        """Get current budget status and alerts."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current_spend = self._daily_spend.get(today, 0.0)
        return {
            "daily_budget_usd": self._daily_budget_usd,
            "current_spend_usd": round(current_spend, 4),
            "remaining_usd": round(max(0, self._daily_budget_usd - current_spend), 4),
            "utilization_pct": round(current_spend / self._daily_budget_usd * 100, 1) if self._daily_budget_usd > 0 else 0,
            "budget_exceeded": current_spend >= self._daily_budget_usd,
            "active_alerts": len([a for a in self._alerts if a.timestamp.strftime("%Y-%m-%d") == today]),
        }

    def get_cost_summary(self) -> dict[str, Any]:
        """Aggregate cost summary across models."""
        by_model: dict[str, dict] = {}
        for record in self._cost_records:
            if record.model_id not in by_model:
                by_model[record.model_id] = {
                    "requests": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_cost_usd": 0.0,
                }
            entry = by_model[record.model_id]
            entry["requests"] += 1
            entry["total_input_tokens"] += record.input_tokens
            entry["total_output_tokens"] += record.output_tokens
            entry["total_cost_usd"] = round(entry["total_cost_usd"] + record.cost_usd, 6)

        return {
            "total_requests": len(self._cost_records),
            "total_cost_usd": round(sum(r.cost_usd for r in self._cost_records), 4),
            "by_model": by_model,
            "budget": self.get_budget_status(),
        }

    def _emit_alert(self, tenant_id: str, current_spend: float, alert_type: str) -> None:
        """Emit a budget alert."""
        alert = BudgetAlert(
            tenant_id=tenant_id,
            current_spend_usd=round(current_spend, 4),
            budget_limit_usd=self._daily_budget_usd,
            alert_type=alert_type,
            timestamp=datetime.now(timezone.utc),
        )
        self._alerts.append(alert)
        logger.warning(
            "BUDGET ALERT [%s]: tenant=%s spend=$%.4f limit=$%.2f",
            alert_type.upper(), tenant_id, current_spend, self._daily_budget_usd,
        )


# ── Singleton ────────────────────────────────────────────────

_router_instance: LiteLLMCostRouter | None = None


def get_cost_router(daily_budget_usd: float = 50.0) -> LiteLLMCostRouter:
    """Get or create the singleton cost router."""
    global _router_instance
    if _router_instance is None:
        _router_instance = LiteLLMCostRouter(daily_budget_usd=daily_budget_usd)
    return _router_instance
