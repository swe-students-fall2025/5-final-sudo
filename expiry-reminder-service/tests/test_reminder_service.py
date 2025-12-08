# expiry-reminder-service/tests/test_reminder_service.py
import os
import sys
import json

# Make sure the expiry-reminder-service directory is on sys.path
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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
    assert (
        compute_risk_level(days_until_expiry=8, importance=3, lead_time_days=20)
        == "HIGH"
    )
    assert (
        compute_risk_level(days_until_expiry=18, importance=3, lead_time_days=20)
        == "MEDIUM"
    )


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
    assert main.get_importance({"importance": "bad", "doc_type": "visa"}) == 5


def test_get_lead_time_and_formatting_helpers():
    assert main.get_lead_time({"renewal_lead_time_days": 15}) == 15
    assert (
        main.get_lead_time({"renewal_lead_time_days": "bad", "doc_type": "visa"}) == 120
    )
    assert main.get_lead_time({"doc_type": "unknown"}) == 30

    assert main.format_in_days(3) == "in 3 days"
    assert main.format_in_days(1) == "in 1 day"
    assert main.format_in_days(0) == "expires today"
    assert main.format_in_days(-2) == "expired 2 days ago"


def test_run_once_updates_only_valid_docs(monkeypatch):
    fake_now = datetime(2024, 1, 1, 12, 0, 0)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
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
    monkeypatch.setattr(
        main, "get_db", lambda: (_ for _ in ()).throw(Exception("boom"))
    )
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


def test_process_digest_recent_window_skips(monkeypatch):
    class FakeCollection:
        def __init__(self, item):
            self.item = item

        def find_one(self, _):
            return self.item

    fixed = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is None else fixed.astimezone(tz)

    # naive last_sent triggers tzinfo correction branch
    state = {"last_digest_at": datetime(2024, 1, 1, 12, 0)}
    db = SimpleNamespace(
        users=FakeCollection({"email": "user@test.com"}),
        notification_state=FakeCollection(state),
    )

    monkeypatch.setattr(main, "ObjectId", lambda x: x)
    monkeypatch.setattr(main, "datetime", FakeDateTime)
    main.process_digest(db, "507f1f77bcf86cd799439011", [], {})


def test_process_digest_mock_mode_updates_state(monkeypatch, capsys):
    fixed = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is None else fixed.astimezone(tz)

    class FakeCollection:
        def __init__(self, item):
            self.item = item
            self.updated = None

        def find_one(self, _):
            return self.item

        def update_one(self, *args, **kwargs):
            self.updated = (args, kwargs)

    urgent_docs = [
        {"name": "Pass", "risk": "CRITICAL", "days_until": 0},
        {"name": "Visa", "risk": "HIGH", "days_until": 5},
    ]
    db = SimpleNamespace(
        users=FakeCollection({"email": "user@test.com", "timezone": "Not/AZone"}),
        notification_state=FakeCollection({}),
    )

    monkeypatch.setattr(main, "ObjectId", lambda x: x)
    monkeypatch.setattr(main, "datetime", FakeDateTime)
    monkeypatch.setenv("EMAIL_MODE", "mock")

    main.process_digest(
        db, "507f1f77bcf86cd799439011", urgent_docs, {"HIGH": 1, "CRITICAL": 1}
    )

    assert db.notification_state.updated is not None
    captured = capsys.readouterr().out
    assert "Pass (CRITICAL): expires today" in captured
    assert "Visa (HIGH): in 5 days" in captured


def test_process_digest_brevo_success_and_failure(monkeypatch):
    fixed = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is None else fixed.astimezone(tz)

    class FakeCollection:
        def __init__(self, item):
            self.item = item
            self.updated = None

        def find_one(self, _):
            return self.item

        def update_one(self, *args, **kwargs):
            self.updated = (args, kwargs)

    user = {"email": "user@test.com", "timezone": "UTC"}
    urgent_docs = [{"name": "Pass", "risk": "CRITICAL", "days_until": 0}]

    # Failure case: brevo_send_email raises, so state not updated
    db_fail = SimpleNamespace(
        users=FakeCollection(user),
        notification_state=FakeCollection({}),
    )
    monkeypatch.setenv("EMAIL_MODE", "brevo")
    monkeypatch.setattr(
        main,
        "brevo_send_email",
        lambda *_, **__: (_ for _ in ()).throw(Exception("fail")),
    )
    monkeypatch.setattr(main, "ObjectId", lambda x: x)
    monkeypatch.setattr(main, "datetime", FakeDateTime)

    main.process_digest(
        db_fail, "507f1f77bcf86cd799439011", urgent_docs, {"CRITICAL": 1}
    )
    assert db_fail.notification_state.updated is None

    # Success case: updates state
    db_success = SimpleNamespace(
        users=FakeCollection(user),
        notification_state=FakeCollection({}),
    )
    monkeypatch.setattr(main, "brevo_send_email", lambda *_, **__: None)
    main.process_digest(
        db_success, "507f1f77bcf86cd799439011", urgent_docs, {"CRITICAL": 1}
    )
    assert db_success.notification_state.updated is not None


def test_process_digest_user_lookup_failure(monkeypatch):
    class FailCollection:
        def find_one(self, _):
            raise Exception("nope")

    db = SimpleNamespace(users=FailCollection(), notification_state=SimpleNamespace())
    monkeypatch.setattr(main, "ObjectId", lambda x: x)
    # Should swallow exception and return without raising
    main.process_digest(db, "uid", [], {})


def test_process_digest_handles_missing_user(monkeypatch):
    class FakeCollection:
        def __init__(self, item):
            self.item = item
            self.updated = False

        def find_one(self, _):
            return self.item

    db = SimpleNamespace(
        users=FakeCollection(None),
        notification_state=FakeCollection({}),
    )
    monkeypatch.setattr(main, "ObjectId", lambda x: x)
    main.process_digest(db, "uid", [], {})
    assert db.notification_state.updated is False


def test_brevo_send_email_happy_path(monkeypatch):
    captured = {}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            captured["read"] = True

    def fake_request(url, data=None, headers=None, method=None):
        captured.update(url=url, data=data, headers=headers, method=method)
        return "req"

    monkeypatch.setenv("BREVO_API_KEY", "k")
    monkeypatch.setenv("BREVO_SENDER_EMAIL", "sender@test.com")
    monkeypatch.setenv("BREVO_SENDER_NAME", "Sender")
    monkeypatch.setattr(main.urllib.request, "Request", fake_request)
    monkeypatch.setattr(
        main.urllib.request, "urlopen", lambda *_args, **_kwargs: DummyResponse()
    )

    main.brevo_send_email("to@test.com", "Hi", "Body")

    assert captured["url"] == "https://api.brevo.com/v3/smtp/email"
    assert captured["method"] == "POST"
    assert json.loads(captured["data"].decode("utf-8"))["subject"] == "Hi"
    assert "read" in captured


def test_brevo_send_email_requires_env(monkeypatch):
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    monkeypatch.delenv("BREVO_SENDER_EMAIL", raising=False)
    with pytest.raises(ValueError):
        main.brevo_send_email("to@test.com", "Hi", "Body")


def test_run_once_calls_process_digest(monkeypatch):
    fixed = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is None else fixed.astimezone(tz)

    docs = [
        {
            "_id": 1,
            "expiry_date": "2024-01-02",
            "importance": 5,
            "renewal_lead_time_days": 10,
            "user_id": "user1",
            "name": "Doc1",
        }
    ]

    class FakeCollection:
        def __init__(self, docs):
            self.docs = docs
            self.updates = []

        def find(self, *_):
            return self.docs

        def update_one(self, *args, **kwargs):
            self.updates.append((args, kwargs))

    called = {}

    def fake_process_digest(db, uid, docs_arg, risk_counts):
        called["args"] = (uid, docs_arg, risk_counts)

    db = SimpleNamespace(documents=FakeCollection(docs))
    monkeypatch.setattr(main, "get_db", lambda: db)
    monkeypatch.setattr(main, "compute_risk_level", lambda **kwargs: "CRITICAL")
    monkeypatch.setattr(main, "process_digest", fake_process_digest)
    monkeypatch.setattr(main, "datetime", FakeDateTime)

    main.run_once()

    assert db.documents.updates, "document should be updated"
    assert called["args"][0] == "user1"
    assert called["args"][1][0]["risk"] == "CRITICAL"


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

- Error handling: if the DB call fails, we log a friendly error instead of blowing up,
  and digest user lookups that explode simply skip.

- KeyboardInterrupt: fakes Ctrl+C so the loop stops, cleans up, and exits cleanly.

- Digests: cooldown respected (7-day window), timezone fallback to UTC, missing user/email
  short-circuits, and both mock and Brevo send paths are covered (including missing envs).

- Helpers: format_in_days, lead time fallback, and Brevo request payload are validated.

"""
