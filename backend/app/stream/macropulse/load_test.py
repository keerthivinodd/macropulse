"""
MacroPulse Agent Load Testing — Day 5 (Pranisree)

Locust script: 50 concurrent NL queries with p50/p95/p99 latency measurement.
Run: locust -f backend/app/stream/macropulse/load_test.py --host http://localhost:8000
"""
from __future__ import annotations

import json
import random
import time

from locust import HttpUser, between, events, task
from locust.runners import MasterRunner

# ── Sample NL queries for load testing ───────────────────────

SAMPLE_QUERIES = [
    "What is the impact of a 50bps repo rate hike on our EBITDA?",
    "How has USD/INR moved in the last 7 days?",
    "What's the current Brent crude price trend?",
    "Show me the G-Sec 10Y yield for the past month",
    "What hedging strategy do you recommend for FX exposure?",
    "How confident are you about the inflation forecast?",
    "What are the data sources for commodity prices?",
    "If oil prices increase by $10, what happens to our COGS?",
    "What is the current CPI index trend?",
    "Run a combined scenario with rate hike and FX depreciation",
    "What is SAIBOR 3M rate today?",
    "How does EIBOR 3M compare with last week?",
    "What's the probability of RBI cutting rates next quarter?",
    "Show me FX volatility for AED/INR",
    "What is the P&L sensitivity to a 2% currency move?",
    "Summarize macro conditions for GCC region",
    "What are the top risks for our treasury this week?",
    "How much is our unhedged exposure in USD?",
    "What's the gold price MoM change?",
    "Show confidence breakdown for the latest macro signal",
    "What are the commodity cost implications for our supply chain?",
    "Run interest rate scenario with +75bps shock",
    "What is the current floating debt ratio impact?",
    "How reliable is the latest FX forecast?",
    "What macro variables should we monitor this week?",
]

TENANT_IDS = ["tenant-india-001", "tenant-gcc-001", "tenant-global-001"]


class MacroPulseNLQueryUser(HttpUser):
    """
    Simulates CFO/finance users sending natural language queries.
    Configured for 50 concurrent users.
    """
    wait_time = between(0.5, 2.0)

    @task(weight=10)
    def nl_query(self):
        """POST /api/v1/macropulse/nl-query with random NL question."""
        payload = {
            "text": random.choice(SAMPLE_QUERIES),
            "tenant_id": random.choice(TENANT_IDS),
            "region": random.choice(["India", "UAE", "Saudi Arabia"]),
        }
        with self.client.post(
            "/api/v1/macropulse/nl-query",
            json=payload,
            catch_response=True,
            name="/api/v1/macropulse/nl-query",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("intent") == "unknown" and data.get("confidence", 0) < 0.5:
                    response.failure("Low confidence unknown intent")
                else:
                    response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(weight=5)
    def scenario_sim(self):
        """POST /api/v1/macropulse/scenario with random parameters."""
        payload = {
            "scenario_type": random.choice(["interest_rate", "fx", "commodity", "combined"]),
            "rate_delta_pct": round(random.uniform(-1.0, 2.0), 2),
            "fx_delta_pct": round(random.uniform(-5.0, 5.0), 2),
            "oil_delta_usd": round(random.uniform(-15.0, 15.0), 2),
            "tenant_id": random.choice(TENANT_IDS),
        }
        with self.client.post(
            "/api/v1/macropulse/scenario",
            json=payload,
            catch_response=True,
            name="/api/v1/macropulse/scenario",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(weight=3)
    def kpi_query(self):
        """GET /api/v1/macropulse/kpi with random metric."""
        metric = random.choice(["repo_rate", "cpi", "usd_inr", "brent", "gsec_10y"])
        with self.client.get(
            f"/api/v1/macropulse/kpi?metric={metric}&limit=30",
            catch_response=True,
            name="/api/v1/macropulse/kpi",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(weight=2)
    def dashboard(self):
        """GET /api/v1/macropulse/dashboard summary tiles."""
        tenant = random.choice(TENANT_IDS)
        with self.client.get(
            f"/api/v1/macropulse/dashboard/{tenant}",
            catch_response=True,
            name="/api/v1/macropulse/dashboard/{tenant_id}",
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


# ── Percentile reporting hook ────────────────────────────────

LATENCIES: list[float] = []


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Collect latencies for percentile calculations."""
    if exception is None:
        LATENCIES.append(response_time)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print p50/p95/p99 latency summary at the end of the test."""
    if not LATENCIES:
        print("\n[MacroPulse Load Test] No successful requests recorded.")
        return

    import numpy as np

    sorted_latencies = np.array(sorted(LATENCIES))
    p50 = np.percentile(sorted_latencies, 50)
    p95 = np.percentile(sorted_latencies, 95)
    p99 = np.percentile(sorted_latencies, 99)
    mean = np.mean(sorted_latencies)
    total = len(sorted_latencies)

    print("\n" + "=" * 60)
    print("  MacroPulse NL Query — Latency Report")
    print("=" * 60)
    print(f"  Total requests : {total}")
    print(f"  Mean latency   : {mean:.1f} ms")
    print(f"  p50 (median)   : {p50:.1f} ms")
    print(f"  p95            : {p95:.1f} ms")
    print(f"  p99            : {p99:.1f} ms")
    print("=" * 60 + "\n")
