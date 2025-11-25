# expiry-reminder-service/logic.py
from typing import Literal, Optional

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def compute_risk_level(
    days_until_expiry: int, importance: int, lead_time_days: Optional[int] = None
) -> RiskLevel:
    if days_until_expiry < 0:
        return "CRITICAL"

    # urgency from time
    if days_until_expiry <= 7:
        base = 3
    elif days_until_expiry <= 30:
        base = 2
    elif days_until_expiry <= 90:
        base = 1
    else:
        base = 0

    # if we're in the reminder window, don't ever call it "LOW"
    if lead_time_days is not None and days_until_expiry <= lead_time_days:
        base = max(base, 1)  # at least MEDIUM

    # let importance actually matter
    if importance >= 5:
        base = min(3, base + 1)
    elif importance <= 2:
        base = max(0, base - 1)

    return ["LOW", "MEDIUM", "HIGH", "CRITICAL"][base]
