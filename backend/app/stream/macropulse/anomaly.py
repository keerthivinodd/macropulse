from __future__ import annotations

from statistics import mean, pstdev


def z_score_flags(values: list[float]) -> dict:
    if len(values) < 3:
        return {"status": "insufficient_data", "z_score": 0.0}

    latest = values[-1]
    avg = mean(values)
    sigma = pstdev(values)
    if sigma == 0:
        return {"status": "stable", "z_score": 0.0}

    z_score = (latest - avg) / sigma
    abs_z = abs(z_score)
    if abs_z > 3.0:
        status = "critical"
    elif abs_z > 2.0:
        status = "watch"
    else:
        status = "normal"

    return {"status": status, "z_score": round(z_score, 2)}
