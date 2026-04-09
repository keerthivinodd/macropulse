"""
P&L Sensitivity Matrix Calculator.
Computes impact of 5 macro variables on tenant P&L.
Results cached in Redis with TTL=300s.
"""
import json
import os
from typing import Any

import redis as redis_lib

from app.stream.macropulse.ingestion.schemas.tenant_profile import TenantProfile

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = 300  # 5 minutes


def _redis() -> redis_lib.Redis:
    return redis_lib.from_url(REDIS_URL)


def calculate_sensitivity_matrix(
    profile: TenantProfile,
    fx_rates: dict[str, float],
    current_brent_usd: float = 80.0,
) -> dict[str, Any]:
    """
    Calculate P&L sensitivity to 5 macro variables.
    All monetary impacts in Crore (Cr), rounded to 2 decimal places.
    """
    results: dict[str, Any] = {}

    # 1. REPO RATE — extra interest per 0.25% hike
    floating_loan_cr = (
        profile.debt.total_loan_amount_cr
        * (profile.debt.floating_proportion_pct / 100)
    )
    repo_impact = round(floating_loan_cr * 0.0025, 4)
    results["REPO_RATE"] = {
        "impact_cr": repo_impact,
        "label": f"₹{repo_impact} Cr extra interest per 0.25% repo rate hike",
        "driver": "floating_loan_book",
        "assumption": "0.25% rate hike, full pass-through",
    }

    # 2. FX USD/INR — P&L impact per 1% move on unhedged exposure
    usd_inr = fx_rates.get("usd_inr", 84.0)
    net_unhedged_usd_m = profile.fx.net_usd_exposure_m * (
        1 - profile.fx.hedge_ratio_pct / 100
    )
    net_unhedged_inr_cr = net_unhedged_usd_m * usd_inr / 10_000_000
    fx_impact = round(abs(net_unhedged_inr_cr) * 0.01, 2)
    results["FX_USD_INR"] = {
        "impact_cr": fx_impact,
        "label": f"₹{fx_impact} Cr P&L impact per 1% USD/INR move on unhedged exposure",
        "driver": "unhedged_usd_exposure",
        "assumption": f"1% USD/INR move, hedge ratio {profile.fx.hedge_ratio_pct}%",
    }

    # 3. CRUDE OIL — COGS increase per $10/bbl rise
    petroleum_cogs_cr = profile.cogs.total_cogs_cr * (profile.cogs.petroleum_pct / 100)
    crude_impact = round(petroleum_cogs_cr * (10 / current_brent_usd), 2)
    results["CRUDE_OIL"] = {
        "impact_cr": crude_impact,
        "label": f"₹{crude_impact} Cr COGS increase per $10/bbl crude price rise",
        "driver": "petroleum_cogs",
        "assumption": f"Brent at ${current_brent_usd}/bbl, $10 rise",
    }

    # 4. WPI INFLATION — COGS increase per 1% WPI rise
    material_pct = (
        profile.cogs.steel_pct
        + profile.cogs.petroleum_pct
        + profile.cogs.electronics_pct
    )
    wpi_impact = round(
        profile.cogs.total_cogs_cr * (material_pct / 100) * 0.01, 2
    )
    results["WPI_INFLATION"] = {
        "impact_cr": wpi_impact,
        "label": f"₹{wpi_impact} Cr COGS increase per 1% WPI inflation rise",
        "driver": "material_cogs",
        "assumption": "1% WPI rise, full pass-through to material costs",
    }

    # 5. GSEC YIELD — MTM loss per 0.5% yield rise
    gsec_impact = round(
        profile.portfolio.modified_duration
        * 0.005
        * profile.portfolio.gsec_holdings_cr,
        2,
    )
    results["GSEC_YIELD"] = {
        "impact_cr": gsec_impact,
        "label": f"₹{gsec_impact} Cr MTM loss per 0.5% G-Sec yield rise",
        "driver": "gsec_portfolio",
        "assumption": f"Modified duration {profile.portfolio.modified_duration}y, 0.5% yield rise",
    }

    # Cache in Redis
    try:
        r = _redis()
        r.setex(
            f"sensitivity:{profile.tenant_id}",
            CACHE_TTL,
            json.dumps(results),
        )
    except Exception:
        pass

    return results


def get_cached_sensitivity(tenant_id: str) -> dict | None:
    """Return cached sensitivity matrix or None if expired/missing."""
    try:
        r = _redis()
        raw = r.get(f"sensitivity:{tenant_id}")
        return json.loads(raw) if raw else None
    except Exception:
        return None
