"""
ETL normalization transforms — pure functions, fully tested.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Timezone registry
# ---------------------------------------------------------------------------

_TZ_MAP: dict[str, str] = {
    "UTC": "UTC",
    "IST": "Asia/Kolkata",
    "AST": "Asia/Riyadh",   # Arabia Standard Time (Saudi)
    "GST": "Asia/Dubai",    # Gulf Standard Time (UAE)
}

# ---------------------------------------------------------------------------
# Confidence tier
# ---------------------------------------------------------------------------

_PRIMARY_SOURCES = {"RBI", "SAMA", "CBUAE", "NSE", "BSE", "EIA"}
_SECONDARY_SOURCES = {"WorldBank", "IMF", "FRED"}


def tag_confidence_tier(source: str) -> str:
    """Return confidence tier based on data source."""
    if source in _PRIMARY_SOURCES:
        return "primary"
    if source in _SECONDARY_SOURCES:
        return "secondary"
    return "tertiary"


# ---------------------------------------------------------------------------
# Currency normalization
# ---------------------------------------------------------------------------

def normalize_currency(
    value: float,
    from_currency: str,
    to_currency: str,
    fx_rates: dict[str, float],
) -> float:
    """
    Convert value from from_currency to to_currency using fx_rates dict.
    fx_rates keys expected as "USD_INR", "AED_INR", "SAR_INR" etc.
    Supported currencies: INR, AED, SAR, USD.
    """
    supported = {"INR", "AED", "SAR", "USD"}
    if from_currency not in supported:
        raise ValueError(f"Unsupported from_currency: {from_currency}")
    if to_currency not in supported:
        raise ValueError(f"Unsupported to_currency: {to_currency}")
    if from_currency == to_currency:
        return value

    # Convert to INR as pivot
    def _to_inr(v: float, ccy: str) -> float:
        if ccy == "INR":
            return v
        key = f"{ccy}_INR"
        if key not in fx_rates:
            raise ValueError(f"Missing fx_rate key: {key}")
        return v * fx_rates[key]

    def _from_inr(v: float, ccy: str) -> float:
        if ccy == "INR":
            return v
        key = f"{ccy}_INR"
        if key not in fx_rates:
            raise ValueError(f"Missing fx_rate key: {key}")
        return v / fx_rates[key]

    inr_value = _to_inr(value, from_currency)
    return round(_from_inr(inr_value, to_currency), 6)


# ---------------------------------------------------------------------------
# Timezone normalization
# ---------------------------------------------------------------------------

def normalize_timezone(dt: datetime, from_tz: str, to_tz: str) -> datetime:
    """
    Convert datetime from from_tz to to_tz.
    Supported: UTC, IST, AST, GST.
    Always store internally in UTC; convert to display tz only at output time.
    """
    if from_tz not in _TZ_MAP:
        raise ValueError(f"Unsupported from_tz: {from_tz}")
    if to_tz not in _TZ_MAP:
        raise ValueError(f"Unsupported to_tz: {to_tz}")

    src_zone = ZoneInfo(_TZ_MAP[from_tz])
    dst_zone = ZoneInfo(_TZ_MAP[to_tz])

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=src_zone)
    else:
        dt = dt.astimezone(src_zone)

    return dt.astimezone(dst_zone)


# ---------------------------------------------------------------------------
# Unit normalization
# ---------------------------------------------------------------------------

_UNIT_CONVERSIONS: dict[str, tuple[float, str]] = {
    "lakh":    (1 / 100,        "Cr"),
    "rupees":  (1 / 10_000_000, "Cr"),
    "millions": (0.83333,       "Cr"),
    "billions": (833.33,        "Cr"),
    "crore":   (1.0,            "Cr"),
}


def normalize_units(value: float, from_unit: str) -> tuple[float, str]:
    """
    Normalize financial units to Crore (Cr).
    Supported from_unit: lakh, rupees, millions, billions, crore.
    Returns (normalized_value, "Cr").
    """
    key = from_unit.lower()
    if key not in _UNIT_CONVERSIONS:
        raise ValueError(f"Unsupported unit: {from_unit}")
    factor, unit_label = _UNIT_CONVERSIONS[key]
    return round(value * factor, 6), unit_label
