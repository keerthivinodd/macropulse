from datetime import date, datetime

from pydantic import BaseModel


class MacroRateRecord(BaseModel):
    source: str
    date: date
    region: str = "IN"
    repo_rate_pct: float | None = None
    gsec_10y_yield_pct: float | None = None
    cpi_index: float | None = None
    wpi_index: float | None = None
    # GCC fields
    saibor_3m_pct: float | None = None
    saibor_6m_pct: float | None = None
    eibor_1m_pct: float | None = None
    eibor_3m_pct: float | None = None
    confidence_tier: str = "primary"


class FxRateRecord(BaseModel):
    timestamp: datetime
    usd_inr: float
    aed_inr: float
    sar_inr: float
    source: str
    region: str


class CommodityPriceRecord(BaseModel):
    date: date
    commodity: str
    price_value: float
    unit: str
    currency: str = "USD"
    region: str
    source: str
