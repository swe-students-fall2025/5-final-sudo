# expiry-reminder-service/tests/test_reminder_service.py
import os
import sys

# Make sure the expiry-reminder-service directory is on sys.path
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import main
from logic import compute_risk_level


def test_compute_risk_level_basic():
    # Far away, low importance -> LOW
    assert compute_risk_level(days_until_expiry=180, importance=1) == "LOW"

    # Within a month, high importance -> HIGH
    assert compute_risk_level(days_until_expiry=20, importance=4) == "HIGH"

    # Past expiry -> CRITICAL
    assert compute_risk_level(days_until_expiry=-1, importance=5) == "CRITICAL"


def test_compute_risk_level_windows():
    assert compute_risk_level(days_until_expiry=50, importance=5) == "MEDIUM"
    assert compute_risk_level(days_until_expiry=50, importance=2) == "LOW"
    assert compute_risk_level(days_until_expiry=1, importance=5) == "CRITICAL"
    assert compute_risk_level(days_until_expiry=8, importance=3, lead_time_days=20) == "HIGH"
    assert compute_risk_level(days_until_expiry=18, importance=3, lead_time_days=20) == "MEDIUM"


def test_parse_expiry_date_variants():
    assert main.parse_expiry_date("2024-05-10") == date(2024, 5, 10)
    assert main.parse_expiry_date("2024-05-10T12:00:00Z") == date(2024, 5, 10)
    assert main.parse_expiry_date("") is None
    assert main.parse_expiry_date("not-a-date") is None
    assert main.parse_expiry_date("   ") is None


def test_normalize_and_importance():
    assert main.normalize_doc_type("Passport") == "passport"
    assert main.normalize_doc_type("Unknown type") == "other"
    assert main.get_importance({"importance": 4}) == 4
    assert main.get_importance({"doc_type": "passport"}) == 5
    assert main.get_importance({"category": "subscription"}) == 2
    assert main.get_importance({"doc_type": "something"}) == 3


def test_run_once_updates_only_valid_docs(monkeypatch):
    fake_now = datetime(2024, 1, 1, 12, 0, 0)
    class FakeDateTime(datetime):
        @classmethod
        def utcnow(cls):
            return fake_now

    monkeypatch.setattr(main, "datetime", FakeDateTime)

    docs = [
        {"_id": 1, "expiry_date": "2024-01-11", "importance": 5},
        {"_id": 2, "expiry_date": ""},
    ]

    collection = MagicMock()
    collection.find.return_value = docs
    db = SimpleNamespace(documents=collection)

    monkeypatch.setattr(main, "get_db", lambda: db)
    monkeypatch.setattr(main, "compute_risk_level", lambda **kwargs: "TEST")

    main.run_once()

    collection.update_one.assert_called_once()
    args, _kwargs = collection.update_one.call_args
    assert args[0] == {"_id": 1}
    update = args[1]["$set"]
    assert update["last_days_until"] == 10
    assert update["last_risk"] == "TEST"
    assert update["last_checked_at"] == fake_now


def test_close_db_connection_resets_client():
    class DummyClient:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    client = DummyClient()
    main._client = client

    main.close_db_connection()

    assert client.closed is True
    assert main._client is None


def test_get_mongo_client_creates_and_reuses(monkeypatch):
    main._client = None

    class FakeClient:
        def __init__(self, uri, serverSelectionTimeoutMS=None):
            self.uri = uri
            self.timeout = serverSelectionTimeoutMS
            self.closed = False

        def __getitem__(self, item):
            return {"name": item}

        def close(self):
            self.closed = True

    monkeypatch.setattr(main, "MongoClient", FakeClient)

    first = main.get_mongo_client()
    second = main.get_mongo_client()

    assert first is second
    assert first.uri == main.MONGO_URI
    assert first.timeout == 5000
    assert first["anything"] == {"name": "anything"}
    first.close()
    main._client = None


def test_get_db_returns_named_database(monkeypatch):
    main._client = None

    class FakeClient(dict):
        def __getitem__(self, item):
            return {"db": item}

    monkeypatch.setattr(main, "MongoClient", lambda *args, **kwargs: FakeClient())
    db = main.get_db()
    assert db == {"db": main.MONGO_DB_NAME}


def test_run_once_handles_db_errors(monkeypatch, capsys):
    monkeypatch.setattr(main, "get_db", lambda: (_ for _ in ()).throw(Exception("boom")))
    main.run_once()
    captured = capsys.readouterr().out
    assert "Error connecting/processing DB: boom" in captured


def test_main_exits_after_keyboardinterrupt(monkeypatch):
    calls = {"count": 0}

    def fake_run_once():
        calls["count"] += 1
        if calls["count"] > 1:
            raise KeyboardInterrupt

    monkeypatch.setattr(main, "run_once", fake_run_once)
    monkeypatch.setattr(main, "time", SimpleNamespace(sleep=lambda *_: None))

    closed = {"called": False}
    monkeypatch.setattr(main, "close_db_connection", lambda: closed.update(called=True))

    main.main()

    assert calls["count"] == 2
    assert closed["called"] is True


"""

Tests

- Risk levels: far-away dates stay low; close or expired ones jump to high/critical
  based on how important the document is.

- Expiry parsing: normal ISO dates work; blank or bad strings return None so the
  service skips them instead of crashing.

- Doc types/importance: messy type names get cleaned; saved importance is used if valid;
  unknown types get a safe default importance.

- Run loop: with fake time and DB, good docs get days-left and risk updates; bad or
  missing expiries are skipped with no DB writes.

- Mongo client: only built once, reused later, returns the right database, and can be
  closed without issues.

- Error handling: if the DB call fails, we log a friendly error instead of blowing up.

- KeyboardInterrupt: fakes Ctrl+C so the loop stops, cleans up, and exits cleanly.

"""
