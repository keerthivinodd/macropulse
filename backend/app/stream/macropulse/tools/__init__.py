from app.stream.macropulse.tools import market_docs_retriever  # noqa: F401
from app.stream.macropulse.tools import kpi_sql_tool  # noqa: F401
from app.stream.macropulse.tools import time_series_tool  # noqa: F401
from app.stream.macropulse.tools import scenario_sim_tool  # noqa: F401
from app.stream.macropulse.tools import anomaly_detector  # noqa: F401
from app.stream.macropulse.tools import notification_tool  # noqa: F401
try:
    from app.stream.macropulse.tools import report_export_tool  # noqa: F401
except ModuleNotFoundError:
    # Report export is optional at app startup because charting deps are heavier
    # than the core Day 1-2 platform/runtime stack.
    report_export_tool = None  # type: ignore[assignment]
