from __future__ import annotations

from app.core.ai_orchestration.agent_models import AgentCapability, AgentConfig
from app.core.ai_orchestration.tools.registry import tool_registry
import app.stream.macropulse.tools as _macropulse_tools  # noqa: F401


MACROPULSE_SYSTEM_PROMPT = (
    "You are MacroPulse, the macroeconomic intelligence agent inside IntelliStream. "
    "Transform macro signals from policy, FX, commodity, inflation, and yield sources into CFO-ready "
    "financial impact analysis. Keep outputs region-aware, currency-denominated, confidence-scored, "
    "and explicitly tied to either company profile data or cited market sources. "
    "When confidence is below threshold, mark the output for human review instead of auto-publishing."
)


MACROPULSE_ENABLED_TOOLS = [
    "market_docs_retriever",
    "kpi_sql_tool",
    "time_series_tool",
    "scenario_sim_tool",
    "anomaly_detector",
    "notification_tool",
    "report_export_tool",
]


MACROPULSE_AGENT_CONFIG = AgentConfig(
    agent_type="macropulse_agent",
    display_name="MacroPulse Agent",
    system_prompt=MACROPULSE_SYSTEM_PROMPT,
    capabilities=[
        AgentCapability.REASONING,
        AgentCapability.ANALYSIS,
        AgentCapability.SEARCH,
        AgentCapability.SUMMARIZATION,
    ],
    enabled_tools=MACROPULSE_ENABLED_TOOLS,
    model="gpt-4o",
    temperature=0.2,
    max_tokens=4096,
    confidence_threshold=0.85,
    metadata={
        "module": "stream",
        "product": "macropulse",
        "architecture": "react-style-tool-agent",
    },
)


def get_macropulse_agent_config() -> AgentConfig:
    return MACROPULSE_AGENT_CONFIG


def get_macropulse_tools() -> list[str]:
    return [tool.name for tool in tool_registry.get_tools_for_agent(MACROPULSE_ENABLED_TOOLS)]
