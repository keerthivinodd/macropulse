from app.stream.macropulse.tools.scenario_sim_tool import scenario_sim_tool

def test_interest_rate_shock():
    result = scenario_sim_tool("interest_rate", rate_delta_pct=1.0)
    assert result["scenario_type"] == "interest_rate"
    assert result["impact_cr"] != 0
    assert "confidence_interval_cr" in result

def test_fx_shock():
    result = scenario_sim_tool("fx", fx_delta_pct=5.0)
    assert result["scenario_type"] == "fx"
    assert result["impact_metric"] == "fx_pnl"

def test_commodity_shock():
    result = scenario_sim_tool("commodity", oil_delta_usd=10.0)
    assert result["scenario_type"] == "commodity"
    assert result["impact_metric"] == "cogs"

def test_combined_worst_case():
    result = scenario_sim_tool("combined", rate_delta_pct=2.0, fx_delta_pct=5.0, oil_delta_usd=15.0)
    assert result["scenario_type"] == "combined"
    assert result["impact_metric"] == "ebitda"
    assert result["components"]["interest_outflow_cr"] != 0
    assert result["components"]["fx_pnl_cr"] != 0
    assert result["components"]["cogs_impact_cr"] != 0

def test_confidence_interval_bounds():
    result = scenario_sim_tool("interest_rate", rate_delta_pct=1.0)
    low = result["confidence_interval_cr"]["low"]
    high = result["confidence_interval_cr"]["high"]
    assert low < result["impact_cr"] < high

def test_zero_shock_returns_zero_impact():
    result = scenario_sim_tool("interest_rate", rate_delta_pct=0.0)
    assert result["impact_cr"] == 0.0
