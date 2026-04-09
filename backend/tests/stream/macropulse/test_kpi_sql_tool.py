"""
Tests for kpi_sql_tool — Day 1 Pranisree task.
Uses SQLite in-memory DB to validate SQL logic without needing Postgres.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────

def _make_mock_row(date: str, value: float):
    row = MagicMock()
    row._mapping = {"date": date, "value": value}
    return row


def _make_db_context(rows):
    """Build an async context manager mock that returns given rows."""
    result_mock = MagicMock()
    result_mock.fetchall.return_value = rows

    execute_mock = AsyncMock(return_value=result_mock)

    db_mock = AsyncMock()
    db_mock.execute = execute_mock

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ── Tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kpi_sql_tool_repo_rate_returns_rows():
    """kpi_sql_tool should return rows for a known metric."""
    rows = [_make_mock_row("2024-10-01", 6.50), _make_mock_row("2024-08-01", 6.50)]

    with patch("app.stream.macropulse.tools.kpi_sql_tool.async_session", return_value=_make_db_context(rows)):
        from app.stream.macropulse.tools.kpi_sql_tool import kpi_sql_tool
        result = await kpi_sql_tool(metric="repo_rate")

    assert result["success"] is True
    assert result["metric"] == "repo_rate"
    assert len(result["rows"]) == 2
    assert result["rows"][0]["value"] == 6.50


@pytest.mark.asyncio
async def test_kpi_sql_tool_cpi_returns_rows():
    """kpi_sql_tool should work for cpi metric."""
    rows = [_make_mock_row("2024-10-01", 5.49)]

    with patch("app.stream.macropulse.tools.kpi_sql_tool.async_session", return_value=_make_db_context(rows)):
        from app.stream.macropulse.tools.kpi_sql_tool import kpi_sql_tool
        result = await kpi_sql_tool(metric="cpi", limit=1)

    assert result["success"] is True
    assert result["rows"][0]["value"] == 5.49


@pytest.mark.asyncio
async def test_kpi_sql_tool_unknown_metric_returns_error():
    """kpi_sql_tool should return success=False for unmapped metrics."""
    from app.stream.macropulse.tools.kpi_sql_tool import kpi_sql_tool

    result = await kpi_sql_tool(metric="unknown_metric_xyz")

    assert result["success"] is False
    assert "error" in result
    assert result["rows"] == []


@pytest.mark.asyncio
async def test_kpi_sql_tool_limit_capped_at_120():
    """limit should be capped at 120 rows max."""
    rows = [_make_mock_row("2024-01-01", 6.50)] * 10

    with patch("app.stream.macropulse.tools.kpi_sql_tool.async_session", return_value=_make_db_context(rows)):
        from app.stream.macropulse.tools.kpi_sql_tool import kpi_sql_tool
        result = await kpi_sql_tool(metric="repo_rate", limit=9999)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_kpi_sql_tool_db_error_returns_graceful_failure():
    """kpi_sql_tool should catch DB exceptions and return success=False."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=Exception("DB connection refused"))
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.stream.macropulse.tools.kpi_sql_tool.async_session", return_value=cm):
        from app.stream.macropulse.tools.kpi_sql_tool import kpi_sql_tool
        result = await kpi_sql_tool(metric="brent")

    assert result["success"] is False
    assert "DB connection refused" in result["error"]


@pytest.mark.asyncio
async def test_kpi_sql_tool_all_supported_metrics():
    """All four supported metrics should resolve to a SQL query."""
    from app.stream.macropulse.tools.kpi_sql_tool import kpi_sql_tool

    rows = [_make_mock_row("2024-10-01", 83.80)]

    for metric in ["repo_rate", "cpi", "usd_inr", "brent"]:
        with patch("app.stream.macropulse.tools.kpi_sql_tool.async_session", return_value=_make_db_context(rows)):
            result = await kpi_sql_tool(metric=metric)
        assert result["success"] is True, f"Expected success for metric={metric}"
