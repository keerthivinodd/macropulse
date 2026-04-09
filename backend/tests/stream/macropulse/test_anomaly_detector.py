from app.stream.macropulse.tools.anomaly_detector import anomaly_detector

def test_normal_series():
    result = anomaly_detector([1.0, 1.1, 1.0, 0.9, 1.0, 1.1, 1.0])
    assert result["status"] == "normal"
    assert result["alert_classification"] == "P3"

def test_critical_spike():
    # Large series with a massive outlier guarantees z > 3.0
    base = [1.0] * 50
    base.append(1000.0)
    result = anomaly_detector(base)
    assert result["status"] == "critical"
    assert result["alert_classification"] == "P1"

def test_watch_level():
    result = anomaly_detector([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 4.0])
    assert result["status"] in ("watch", "critical")
    assert result["alert_classification"] in ("P1", "P2")

def test_insufficient_data():
    result = anomaly_detector([1.0, 2.0])
    assert result["status"] == "insufficient_data"
    assert result["alert_classification"] == "info"

def test_stable_flat_series():
    result = anomaly_detector([5.0, 5.0, 5.0, 5.0, 5.0])
    assert result["status"] == "stable"

def test_input_points_count():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = anomaly_detector(values)
    assert result["input_points"] == 5
