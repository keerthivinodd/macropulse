"""
Tenant financial profile schemas — Pydantic v2.
"""
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class DebtProfile(BaseModel):
    total_loan_amount_cr: float
    rate_type: Literal["MCLR", "Fixed", "Floating"]
    current_effective_rate_pct: float
    floating_proportion_pct: float  # 0–100
    short_term_debt_cr: float
    long_term_debt_cr: float


class FXExposure(BaseModel):
    net_usd_exposure_m: float
    net_aed_exposure_m: float
    net_sar_exposure_m: float
    hedge_ratio_pct: float  # 0–100
    hedge_instrument: Literal["Forward", "Options", "Natural", "None"]


class COGSProfile(BaseModel):
    total_cogs_cr: float
    steel_pct: float
    petroleum_pct: float
    electronics_pct: float
    freight_pct: float
    other_pct: float

    @model_validator(mode="after")
    def validate_pcts_sum(self) -> "COGSProfile":
        total = (
            self.steel_pct
            + self.petroleum_pct
            + self.electronics_pct
            + self.freight_pct
            + self.other_pct
        )
        if not (99.0 <= total <= 101.0):
            raise ValueError(f"COGS percentages must sum to 100, got {total:.2f}")
        return self


class InvestmentPortfolio(BaseModel):
    gsec_holdings_cr: float
    modified_duration: float  # years


class LogisticsProfile(BaseModel):
    primary_routes: list[str]
    monthly_shipment_value_cr: float
    inventory_buffer_days: int


class NotificationConfig(BaseModel):
    email: str | None = None
    teams_webhook: str | None = None
    slack_webhook: str | None = None
    channels: list[Literal["email", "teams", "slack"]] = Field(default_factory=list)


class TenantProfile(BaseModel):
    tenant_id: str
    company_name: str
    primary_region: Literal["IN", "UAE", "SA"]
    primary_currency: Literal["INR", "AED", "SAR"]
    debt: DebtProfile
    fx: FXExposure
    cogs: COGSProfile
    portfolio: InvestmentPortfolio
    logistics: LogisticsProfile
    notification_config: NotificationConfig = Field(default_factory=NotificationConfig)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
