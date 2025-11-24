# expiry-reminder-service/tests/test_reminder_service.py
import os
import sys

# Make sure the expiry-reminder-service directory (where reminder_service/ lives) is on sys.path
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from reminder_service.logic import compute_risk_level


def test_compute_risk_level_basic():
    # Far away, low importance -> LOW
    assert compute_risk_level(days_until_expiry=180, importance=1) == "LOW"

    # Within a month, high importance -> HIGH
    assert compute_risk_level(days_until_expiry=20, importance=4) == "HIGH"

    # Past expiry -> CRITICAL
    assert compute_risk_level(days_until_expiry=-1, importance=5) == "CRITICAL"
