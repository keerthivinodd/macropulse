from __future__ import annotations

from app.core.ai_orchestration.tools.registry import tool_registry
from app.stream.macropulse.company_profile import DEFAULT_COMPANY_PROFILE
from app.stream.macropulse.tool_schemas import SCENARIO_SIM_TOOL_SCHEMA


def _currency_prefix(currency: str) -> str:
    return {"INR": "Rs.", "AED": "AED ", "SAR": "SAR "}.get(currency, f"{currency} ")


def _round_cr(amount: float) -> float:
    return round(amount, 2)


@tool_registry.register(
    name="scenario_sim_tool",
    description="Run MacroPulse what-if simulations for interest, FX, commodity, and combined shocks",
    parameters_schema=SCENARIO_SIM_TOOL_SCHEMA,
)
def scenario_sim_tool(
    scenario_type: str,
    rate_delta_pct: float = 0.0,
    fx_delta_pct: float = 0.0,
    oil_delta_usd: float = 0.0,
    tenant_id: str | None = None,
) -> dict:
    from app.stream.macropulse.tenant_profile_api import _profiles
    from app.stream.macropulse.company_profile import (
        CompanyMacroProfile, DebtProfile, FxExposureProfile,
        CostStructureProfile, InvestmentProfile,
    )

    if tenant_id and tenant_id in _profiles:
        p = _profiles[tenant_id]
        profile = CompanyMacroProfile(
            primary_currency=p["primary_currency"],
            primary_region=p["primary_region"],
            debt=DebtProfile(
                total_loan_amount_cr=p["total_loan_amount_cr"],
                floating_ratio=p["floating_ratio"],
            ),
            fx=FxExposureProfile(
                usd_exposure_m=p["usd_exposure_m"],
                hedge_ratio_pct=p["hedge_ratio_pct"],
                unhedged_inr_equivalent_cr=p["usd_exposure_m"] * 83.0 * (1 - p["hedge_ratio_pct"] / 100),
            ),
            costs=CostStructureProfile(
                total_cogs_cr=p["total_cogs_cr"],
                plastic_pct=p["plastic_pct"],
            ),
            investments=InvestmentProfile(
                gsec_amount_cr=p["gsec_amount_cr"],
                modified_duration=p["modified_duration"],
            ),
        )
    else:
        profile = DEFAULT_COMPANY_PROFILE
    floating_share = profile.debt.floating_ratio if profile.debt.rate_type == "Floating" else 0.0

    interest_impact_cr = (
        profile.debt.total_loan_amount_cr * (rate_delta_pct / 100.0) * floating_share
    )

    unhedged_share = max(0.0, 1.0 - (profile.fx.hedge_ratio_pct / 100.0))
    fx_impact_cr = profile.fx.unhedged_inr_equivalent_cr * (fx_delta_pct / 100.0)
    fx_unhedged_exposure_cr = profile.fx.unhedged_inr_equivalent_cr * unhedged_share

    base_oil_price = 80.0
    petroleum_component_cr = (profile.costs.plastic_pct / 100.0) * profile.costs.total_cogs_cr
    commodity_impact_cr = petroleum_component_cr * (oil_delta_usd / base_oil_price)

    gsec_mtm_impact_cr = -1 * profile.investments.gsec_amount_cr * profile.investments.modified_duration * (
        rate_delta_pct / 100.0
    )
    combined_ebitda_impact_cr = interest_impact_cr + fx_impact_cr + commodity_impact_cr + gsec_mtm_impact_cr

    scenario_key = scenario_type.lower().strip()
    currency = profile.primary_currency
    prefix = _currency_prefix(currency)

    outputs = {
        "interest_rate": {
            "headline": (
                f"A {rate_delta_pct:.2f}% rate hike increases annual borrowing costs by "
                f"{prefix}{_round_cr(interest_impact_cr)} Cr"
            ),
            "impact_cr": _round_cr(interest_impact_cr),
            "metric": "interest_outflow",
        },
        "fx": {
            "headline": (
                f"A {fx_delta_pct:.2f}% move in FX creates an estimated "
                f"{prefix}{_round_cr(fx_impact_cr)} Cr mark-to-market impact on unhedged exposure"
            ),
            "impact_cr": _round_cr(fx_impact_cr),
            "metric": "fx_pnl",
        },
        "commodity": {
            "headline": (
                f"Every ${oil_delta_usd:.2f} oil move changes annual COGS by "
                f"{prefix}{_round_cr(commodity_impact_cr)} Cr"
            ),
            "impact_cr": _round_cr(commodity_impact_cr),
            "metric": "cogs",
        },
        "combined": {
            "headline": (
                f"Combined macro scenario shifts EBITDA by {prefix}{_round_cr(combined_ebitda_impact_cr)} Cr"
            ),
            "impact_cr": _round_cr(combined_ebitda_impact_cr),
            "metric": "ebitda",
        },
    }

    selected = outputs.get(scenario_key, outputs["combined"])
    return {
        "scenario_type": scenario_key,
        "company_name": profile.company_name,
        "primary_region": profile.primary_region,
        "primary_currency": currency,
        "headline": selected["headline"],
        "impact_metric": selected["metric"],
        "impact_cr": selected["impact_cr"],
        "confidence_interval_cr": {
            "low": _round_cr(selected["impact_cr"] * 0.9),
            "high": _round_cr(selected["impact_cr"] * 1.1),
        },
        "assumptions": {
            "floating_share": round(floating_share, 2),
            "unhedged_exposure_cr": _round_cr(fx_unhedged_exposure_cr),
            "base_oil_price_usd": base_oil_price,
            "modified_duration": profile.investments.modified_duration,
        },
        "components": {
            "interest_outflow_cr": _round_cr(interest_impact_cr),
            "fx_pnl_cr": _round_cr(fx_impact_cr),
            "cogs_impact_cr": _round_cr(commodity_impact_cr),
            "gsec_mtm_cr": _round_cr(gsec_mtm_impact_cr),
        },
    }
