from __future__ import annotations

from datetime import UTC, datetime

from app.stream.macropulse.company_profile import DEFAULT_COMPANY_PROFILE
from app.stream.macropulse.schemas import (
    MacroPulseIngestionPlanItem,
    MacroPulseIngestionPlanResponse,
    MacroPulseSourceCatalogEntry,
    MacroPulseSourceCatalogResponse,
)


SOURCE_CATALOG: list[MacroPulseSourceCatalogEntry] = [
    MacroPulseSourceCatalogEntry(
        id="rbi_official_api",
        category="central_bank_policy",
        name="RBI Official API",
        provider_type="official",
        access="free",
        cadence="real_time",
        regions=["India"],
        url="https://api.rbi.org.in",
        coverage="Policy rates, MPC minutes, circulars, forex reference rates",
        notes="Primary India policy authority",
    ),
    MacroPulseSourceCatalogEntry(
        id="rbi_dbie",
        category="central_bank_policy",
        name="RBI DBIE",
        provider_type="official",
        access="free",
        cadence="daily",
        regions=["India"],
        url="https://dbie.rbi.org.in/DBIE/dbie.rbi",
        coverage="Historical G-Sec yields, CPI, WPI, forex, macro time-series",
        notes="Historical India macro backbone",
    ),
    MacroPulseSourceCatalogEntry(
        id="sama_economic_reports",
        category="central_bank_policy",
        name="SAMA Economic Reports",
        provider_type="official",
        access="free",
        cadence="daily",
        regions=["Saudi Arabia"],
        url="https://www.sama.gov.sa/en-US/EconomicReports",
        coverage="SAIBOR, policy decisions, economic reports",
    ),
    MacroPulseSourceCatalogEntry(
        id="cbuae_statistics",
        category="central_bank_policy",
        name="CBUAE Statistics",
        provider_type="official",
        access="free",
        cadence="daily",
        regions=["UAE"],
        url="https://www.centralbank.ae/en/statistics",
        coverage="EIBOR, policy circulars, UAE monetary statistics",
    ),
    MacroPulseSourceCatalogEntry(
        id="nse_india_api",
        category="fx_market_data",
        name="NSE India API",
        provider_type="market",
        access="free",
        cadence="real_time",
        regions=["India"],
        url="https://www.nseindia.com/api",
        coverage="Nifty, Bank Nifty, currency derivatives including USD/INR and EUR/INR futures",
    ),
    MacroPulseSourceCatalogEntry(
        id="alpha_vantage",
        category="fx_market_data",
        name="Alpha Vantage",
        provider_type="market",
        access="api_key",
        cadence="real_time",
        regions=["Global", "India", "UAE", "Saudi Arabia"],
        url="https://www.alphavantage.co/query?function=FX_INTRADAY",
        coverage="FX rates, equity indices, crypto, selected commodity prices",
        requires_api_key=True,
        enabled_for_current_build=False,
    ),
    MacroPulseSourceCatalogEntry(
        id="open_exchange_rates",
        category="fx_market_data",
        name="Open Exchange Rates",
        provider_type="market",
        access="api_key",
        cadence="real_time",
        regions=["Global", "India", "UAE", "Saudi Arabia"],
        url="https://openexchangerates.org/api/latest.json",
        coverage="Multi-currency FX including USD/INR, AED/INR, SAR/INR",
        requires_api_key=True,
        enabled_for_current_build=False,
    ),
    MacroPulseSourceCatalogEntry(
        id="fixer",
        category="fx_market_data",
        name="Fixer.io",
        provider_type="market",
        access="api_key",
        cadence="real_time",
        regions=["Global", "India", "UAE", "Saudi Arabia"],
        url="https://data.fixer.io/api/latest",
        coverage="Intraday and historical ECB-backed FX rates",
        requires_api_key=True,
        enabled_for_current_build=False,
    ),
    MacroPulseSourceCatalogEntry(
        id="tadawul",
        category="fx_market_data",
        name="Tadawul",
        provider_type="market",
        access="free",
        cadence="real_time",
        regions=["Saudi Arabia"],
        url="https://www.saudiexchange.sa/wps/portal/saudiexchange",
        coverage="TASI index and Saudi market data",
    ),
    MacroPulseSourceCatalogEntry(
        id="dfm_adx",
        category="fx_market_data",
        name="DFM / ADX",
        provider_type="market",
        access="free",
        cadence="real_time",
        regions=["UAE"],
        url="https://www.dfm.ae/market-data",
        coverage="DFM General Index and AED market data",
    ),
    MacroPulseSourceCatalogEntry(
        id="eia_api_v2",
        category="commodity_prices",
        name="EIA API v2",
        provider_type="official",
        access="free_key",
        cadence="daily",
        regions=["Global"],
        url="https://api.eia.gov/v2/petroleum/pri/spt/data",
        coverage="WTI, Brent, natural gas, petroleum products",
        notes="Authoritative US energy source",
        requires_api_key=True,
        enabled_for_current_build=False,
    ),
    MacroPulseSourceCatalogEntry(
        id="world_bank_commodity",
        category="commodity_prices",
        name="World Bank Commodity API",
        provider_type="official",
        access="free",
        cadence="monthly",
        regions=["Global"],
        url="https://api.worldbank.org/v2/en/indicator/PCOALAUUSDM",
        coverage="Metals, agriculture, energy, fertilizers",
    ),
    MacroPulseSourceCatalogEntry(
        id="nasdaq_data_link",
        category="commodity_prices",
        name="Nasdaq Data Link",
        provider_type="market",
        access="api_key",
        cadence="daily",
        regions=["Global"],
        url="https://data.nasdaq.com/api/v3/datasets/LBMA/GOLD",
        coverage="Commodity futures including metals and grains",
        requires_api_key=True,
        enabled_for_current_build=False,
    ),
    MacroPulseSourceCatalogEntry(
        id="commodity_price_api",
        category="commodity_prices",
        name="Commodity Price API",
        provider_type="market",
        access="api_key",
        cadence="real_time",
        regions=["Global"],
        url="https://commodities-api.com/api/latest",
        coverage="Real-time crude, gold, copper, aluminium, coal",
        requires_api_key=True,
        enabled_for_current_build=False,
    ),
    MacroPulseSourceCatalogEntry(
        id="fred",
        category="commodity_prices",
        name="FRED",
        provider_type="official",
        access="free_key",
        cadence="daily",
        regions=["Global"],
        url="https://api.stlouisfed.org/fred/series/observations",
        coverage="US Fed rate, PPI, global commodity and macro series",
        requires_api_key=True,
        enabled_for_current_build=False,
    ),
    MacroPulseSourceCatalogEntry(
        id="mospi",
        category="inflation_statistics",
        name="MOSPI",
        provider_type="official",
        access="free",
        cadence="monthly",
        regions=["India"],
        url="https://mospi.gov.in",
        coverage="India CPI, WPI, IIP",
    ),
    MacroPulseSourceCatalogEntry(
        id="gastat",
        category="inflation_statistics",
        name="GASTAT",
        provider_type="official",
        access="free",
        cadence="monthly",
        regions=["Saudi Arabia"],
        url="https://www.stats.gov.sa/en/api",
        coverage="Saudi GDP, CPI, trade statistics, social indicators",
    ),
    MacroPulseSourceCatalogEntry(
        id="fcsa",
        category="inflation_statistics",
        name="FCSA",
        provider_type="official",
        access="free",
        cadence="monthly",
        regions=["UAE"],
        url="https://fcsc.gov.ae/en-us/Pages/Statistics",
        coverage="UAE CPI, national accounts, trade statistics",
    ),
    MacroPulseSourceCatalogEntry(
        id="imf_data_api",
        category="inflation_statistics",
        name="IMF Data API",
        provider_type="official",
        access="free",
        cadence="monthly",
        regions=["Global", "India", "UAE", "Saudi Arabia"],
        url="https://www.imf.org/external/datamapper/api/v1",
        coverage="Country-level macro statistics and WEO datasets",
    ),
    MacroPulseSourceCatalogEntry(
        id="world_bank_api",
        category="inflation_statistics",
        name="World Bank API",
        provider_type="official",
        access="free",
        cadence="monthly",
        regions=["Global", "India", "UAE", "Saudi Arabia"],
        url="https://api.worldbank.org/v2/country/IN/indicator/FP.CPI.TOTL.ZG",
        coverage="GDP growth, trade balance, debt/GDP, inflation",
    ),
    MacroPulseSourceCatalogEntry(
        id="snp_global_pmi",
        category="inflation_statistics",
        name="PMI (S&P Global)",
        provider_type="premium",
        access="enterprise",
        cadence="monthly",
        regions=["India", "UAE", "Saudi Arabia"],
        url="https://www.spglobal.com/marketintelligence/en/mi/products/pmi.html",
        coverage="Manufacturing and services PMI",
        enabled_for_current_build=False,
    ),
    MacroPulseSourceCatalogEntry(
        id="newsapi",
        category="news_signal_corpora",
        name="NewsAPI.org",
        provider_type="news",
        access="api_key",
        cadence="hourly",
        regions=["Global", "India", "UAE", "Saudi Arabia"],
        url="https://newsapi.org/v2/everything",
        coverage="Aggregated Economic Times, Mint, Gulf News, Arab News, Argaam coverage",
        requires_api_key=True,
        enabled_for_current_build=False,
    ),
    MacroPulseSourceCatalogEntry(
        id="gnews",
        category="news_signal_corpora",
        name="GNews API",
        provider_type="news",
        access="api_key",
        cadence="hourly",
        regions=["Global", "India", "UAE", "Saudi Arabia"],
        url="https://gnews.io/api/v4/search",
        coverage="Global news with language and country filters",
        requires_api_key=True,
        enabled_for_current_build=False,
    ),
    MacroPulseSourceCatalogEntry(
        id="et_mint_rss",
        category="news_signal_corpora",
        name="ET / Mint RSS",
        provider_type="news",
        access="free",
        cadence="hourly",
        regions=["India"],
        url="https://economictimes.indiatimes.com/rssfeedsdefault.cms",
        coverage="Direct RSS feeds for macro, banking, and market news",
    ),
    MacroPulseSourceCatalogEntry(
        id="bloomberg_terminal_api",
        category="premium_optional",
        name="Bloomberg Terminal API",
        provider_type="premium",
        access="enterprise",
        cadence="real_time",
        regions=["Global", "India", "UAE", "Saudi Arabia"],
        url="https://www.bloomberg.com/professional/support/api-library/",
        coverage="Real-time pricing, analytics, and high-quality market news",
        enabled_for_current_build=False,
    ),
    MacroPulseSourceCatalogEntry(
        id="refinitiv_eikon",
        category="premium_optional",
        name="Refinitiv Eikon / LSEG",
        provider_type="premium",
        access="enterprise",
        cadence="real_time",
        regions=["Global", "India", "UAE", "Saudi Arabia"],
        url="https://developers.lseg.com/en/api-catalog/eikon",
        coverage="FX, rates, commodities, and news alternative to Bloomberg",
        enabled_for_current_build=False,
    ),
]


def get_source_catalog() -> MacroPulseSourceCatalogResponse:
    return MacroPulseSourceCatalogResponse(
        generated_at=datetime.now(UTC),
        total_sources=len(SOURCE_CATALOG),
        sources=SOURCE_CATALOG,
    )


def get_ingestion_plan() -> MacroPulseIngestionPlanResponse:
    profile = DEFAULT_COMPANY_PROFILE
    region = profile.primary_region
    currency = profile.primary_currency

    applicable_sources = [
        source for source in SOURCE_CATALOG if "Global" in source.regions or region in source.regions
    ]

    def implementation_status(source: MacroPulseSourceCatalogEntry) -> str:
        if source.access == "enterprise":
            return "premium_blocked"
        if source.requires_api_key and not source.enabled_for_current_build:
            return "key_required"
        return "active" if source.enabled_for_current_build else "planned"

    def priority_for(source: MacroPulseSourceCatalogEntry) -> str:
        if source.provider_type == "official":
            return "P0"
        if source.category in {"fx_market_data", "commodity_prices"}:
            return "P1"
        return "P2"

    purpose_map = {
        "central_bank_policy": "Policy shocks, rates, circulars, and reference rates",
        "fx_market_data": f"Currency and capital-market monitoring in {currency}",
        "commodity_prices": "COGS and raw-material shock transmission",
        "inflation_statistics": "Inflation and macro benchmark validation",
        "news_signal_corpora": "Narrative corroboration and alert context",
        "premium_optional": "Premium latency-sensitive enrichment",
    }

    plan = [
        MacroPulseIngestionPlanItem(
            source_id=source.id,
            source_name=source.name,
            cadence=source.cadence,
            purpose=purpose_map[source.category],
            priority=priority_for(source),
            implementation_status=implementation_status(source),
        )
        for source in applicable_sources
    ]

    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    status_order = {"active": 0, "planned": 1, "key_required": 2, "premium_blocked": 3}
    plan.sort(key=lambda item: (priority_order[item.priority], status_order[item.implementation_status], item.source_name))

    return MacroPulseIngestionPlanResponse(
        generated_at=datetime.now(UTC),
        current_region=region,
        current_currency=currency,
        plan=plan,
    )
