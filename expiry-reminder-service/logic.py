# expiry-reminder-service/logic.py
from typing import Literal

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def compute_risk_level(
    days_until_expiry: int, importance: int, lead_time_days: int = 30
) -> RiskLevel:
    if days_until_expiry < 0:
        return "CRITICAL"

    # Outside reminder window: not urgent yet (but keep a tiny bump for very important docs)
    if days_until_expiry > lead_time_days:
        return "MEDIUM" if importance >= 5 else "LOW"

    # Inside reminder window: scale by how deep into the window you are
    half = max(1, lead_time_days // 2)
    quarter = max(1, lead_time_days // 4)

    if days_until_expiry <= quarter:
        return "CRITICAL"
    if days_until_expiry <= half:
        return "CRITICAL" if importance >= 4 else "HIGH"
    return "HIGH" if importance >= 4 else "MEDIUM"
