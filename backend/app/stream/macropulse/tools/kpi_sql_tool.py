from __future__ import annotations

from sqlalchemy import text

from app.database import async_session
from app.core.ai_orchestration.tools.registry import tool_registry
from app.stream.macropulse.tool_schemas import KPI_SQL_TOOL_SCHEMA


METRIC_SQL = {
    # Reads from Keerthi's macro_rates table (RBI connector)
    "repo_rate": "SELECT date, repo_rate_pct AS value FROM macro_rates WHERE repo_rate_pct IS NOT NULL ORDER BY date DESC LIMIT :limit",
    "cpi": "SELECT date, cpi_index AS value FROM macro_rates WHERE cpi_index IS NOT NULL ORDER BY date DESC LIMIT :limit",
    # Reads from Keerthi's fx_rates table
    "usd_inr": "SELECT date, value FROM macro_kpis WHERE metric = 'usd_inr' ORDER BY date DESC LIMIT :limit",
    # Reads from Keerthi's commodity_prices table
    "brent": "SELECT date, value FROM macro_kpis WHERE metric = 'brent' ORDER BY date DESC LIMIT :limit",
    # GCC rates from macro_rates
    "saibor_3m": "SELECT date, saibor_3m_pct AS value FROM macro_rates WHERE saibor_3m_pct IS NOT NULL ORDER BY date DESC LIMIT :limit",
    "eibor_3m": "SELECT date, eibor_3m_pct AS value FROM macro_rates WHERE eibor_3m_pct IS NOT NULL ORDER BY date DESC LIMIT :limit",
    "gsec_10y": "SELECT date, gsec_10y_yield_pct AS value FROM macro_rates WHERE gsec_10y_yield_pct IS NOT NULL ORDER BY date DESC LIMIT :limit",
}


@tool_registry.register(
    name="kpi_sql_tool",
    description="Retrieve structured macro KPI time-series from the warehouse or operational SQL store",
    parameters_schema=KPI_SQL_TOOL_SCHEMA,
)
async def kpi_sql_tool(metric: str, start_date: str | None = None, end_date: str | None = None, limit: int = 30) -> dict:
    sql = METRIC_SQL.get(metric)
    if not sql:
        return {
            "metric": metric,
            "rows": [],
            "success": False,
            "error": "Metric is not mapped yet. Add a warehouse query mapping for this KPI.",
        }

    try:
        async with async_session() as db:
            result = await db.execute(text(sql), {"limit": min(limit, 120)})
            rows = [dict(row._mapping) for row in result.fetchall()]
        return {
            "metric": metric,
            "start_date": start_date,
            "end_date": end_date,
            "rows": rows,
            "success": True,
            "source": "sql_warehouse_adapter",
        }
    except Exception as exc:
        return {
            "metric": metric,
            "rows": [],
            "success": False,
            "error": str(exc),
            "source": "sql_warehouse_adapter",
        }
