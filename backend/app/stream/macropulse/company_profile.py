from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


CurrencyCode = Literal["INR", "AED", "SAR"]
RegionCode = Literal["India", "UAE", "Saudi Arabia"]
RateType = Literal["MCLR", "Fixed", "Floating"]


@dataclass
class DebtProfile:
    total_loan_amount_cr: float = 100.0
    rate_type: RateType = "Floating"
    current_effective_rate_pct: float = 8.75
    short_term_amount_cr: float = 35.0
    long_term_amount_cr: float = 65.0
    floating_ratio: float = 0.65


@dataclass
class FxExposureProfile:
    usd_exposure_m: float = 12.0
    usd_position: Literal["Long", "Short"] = "Long"
    aed_exposure_m: float = 0.0
    sar_exposure_m: float = 0.0
    hedge_ratio_pct: float = 45.0
    unhedged_inr_equivalent_cr: float = 54.0


@dataclass
class CostStructureProfile:
    steel_pct: float = 12.0
    steel_value_cr: float = 48.0
    plastic_pct: float = 9.0
    electronics_pct: float = 16.0
    freight_pct: float = 7.0
    total_cogs_cr: float = 400.0


@dataclass
class InvestmentProfile:
    gsec_amount_cr: float = 75.0
    duration_years: float = 4.2
    modified_duration: float = 3.8


@dataclass
class LogisticsProfile:
    primary_routes: list[str] = field(default_factory=lambda: ["Mumbai-Dubai", "Chennai-Jebel Ali"])
    shipment_value_cr: float = 18.0
    buffer_days: int = 21


@dataclass
class CompanyMacroProfile:
    company_name: str = "Fidelis Demo Manufacturing"
    primary_region: RegionCode = "India"
    primary_currency: CurrencyCode = "INR"
    debt: DebtProfile = field(default_factory=DebtProfile)
    fx: FxExposureProfile = field(default_factory=FxExposureProfile)
    costs: CostStructureProfile = field(default_factory=CostStructureProfile)
    investments: InvestmentProfile = field(default_factory=InvestmentProfile)
    logistics: LogisticsProfile = field(default_factory=LogisticsProfile)


DEFAULT_COMPANY_PROFILE = CompanyMacroProfile()
