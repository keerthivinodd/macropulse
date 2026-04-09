from __future__ import annotations


MARKET_DOCS_RETRIEVER_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Macro query or policy topic to search for"},
        "region": {"type": "string", "description": "Primary region such as India, UAE, or Saudi Arabia"},
        "top_k": {"type": "integer", "default": 5, "description": "Number of results to return"},
        "collection": {"type": "string", "default": "macropulse_market_docs", "description": "Vector collection name"},
    },
    "required": ["query"],
}

KPI_SQL_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "metric": {"type": "string", "description": "Metric key such as repo_rate, cpi, usd_inr, brent"},
        "start_date": {"type": "string", "description": "ISO date filter start"},
        "end_date": {"type": "string", "description": "ISO date filter end"},
        "limit": {"type": "integer", "default": 30, "description": "Max rows to return"},
    },
    "required": ["metric"],
}

SCENARIO_SIM_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "scenario_type": {"type": "string", "description": "interest_rate, fx, commodity, combined"},
        "rate_delta_pct": {"type": "number", "description": "Rate shock in percentage points"},
        "fx_delta_pct": {"type": "number", "description": "FX shock in percentage terms"},
        "oil_delta_usd": {"type": "number", "description": "Oil shock in USD per barrel"},
        "tenant_id": {"type": "string", "description": "Optional tenant ID to use tenant-specific profile"},
    },
    "required": ["scenario_type"],
}

ANOMALY_DETECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "values": {
            "type": "array",
            "items": {"type": "number"},
            "description": "Ordered KPI observations",
        },
    },
    "required": ["values"],
}

TIME_SERIES_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "values": {
            "type": "array",
            "items": {"type": "number"},
            "description": "Ordered KPI observations",
        },
        "label": {
            "type": "string",
            "description": "Human-friendly label for the series",
            "default": "series",
        },
    },
    "required": ["values"],
}

NOTIFICATION_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "message": {"type": "string"},
        "severity": {"type": "string", "description": "P1, P2, or P3"},
        "channel": {"type": "string", "description": "teams, slack, email, webhook"},
    },
    "required": ["title", "message", "severity"],
}

REPORT_EXPORT_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "format": {"type": "string", "default": "html", "description": "html or pdf"},
    },
    "required": ["title", "summary"],
}
