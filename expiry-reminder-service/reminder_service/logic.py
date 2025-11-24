# expiry-reminder-service/reminder_service/logic.py
from typing import Literal

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def compute_risk_level(days_until_expiry: int, importance: int) -> RiskLevel:
    """Compute a simple risk level for an expiring document.

    This is pure logic with no I/O so it's easy to test.
    You can refine the algorithm later.
    """
    if days_until_expiry < 0:
        return "CRITICAL"

    # Very soon
    if days_until_expiry <= 7:
        return "CRITICAL" if importance >= 3 else "HIGH"

    # Coming up this month
    if days_until_expiry <= 30:
        return "HIGH" if importance >= 3 else "MEDIUM"

    # Within the next few months
    if days_until_expiry <= 90:
        return "MEDIUM"

    # Far in the future
    return "LOW"
