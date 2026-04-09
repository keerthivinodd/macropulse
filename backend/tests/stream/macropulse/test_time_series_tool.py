from app.stream.macropulse.tools.time_series_tool import time_series_tool

def test_basic_output():
    result = time_series_tool([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result["success"] is True
    assert result["latest"] == 5.0
    assert result["trend"] == "up"

def test_too_few_points():
    result = time_series_tool([5.0])
    assert result["success"] is False

def test_downtrend():
    result = time_series_tool([10.0, 9.0, 8.0, 7.0, 6.0])
    assert result["trend"] == "down"

def test_cagr_positive():
    result = time_series_tool([100.0, 110.0, 121.0])
    assert result["cagr_pct"] > 0

def test_momentum_score():
    result = time_series_tool([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0])
    assert result["momentum_score_pct"] > 0

def test_rolling_avg_uses_full_series_when_short():
    result = time_series_tool([5.0, 6.0, 7.0])
    assert result["rolling_avg_30"] == result["mean"]
