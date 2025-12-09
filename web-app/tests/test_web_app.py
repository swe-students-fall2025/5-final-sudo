# web-app/tests/test_web_app.py
import os
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime, date, timedelta
from bson import ObjectId
from werkzeug.security import generate_password_hash
from pymongo.errors import DuplicateKeyError

# Make sure the web-app directory (where main.py lives) is on sys.path
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set env var for testing before import
os.environ["SECRET_KEY"] = "test-secret"
from main import app
from routers.documents import (
    parse_date_loose,
    parse_date_strict,
    compute_days_until,
    compute_risk_level,
    compute_status,
    build_name,
    coerce_importance,
    coerce_lead_time,
    normalize_doc_type,
    _jsonify_value,
    _serialize_doc,
)

""" test to check health"""


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


""" test to check if new users can register"""


def test_register_new():
    client = app.test_client()
    with patch("main.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.users.insert_one.return_value.inserted_id = "507f1f77bcf86cd799439011"

        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "nice123456",
                "timezone": "UTC",
            },
        )
        assert response.status_code == 201


""" test to check if already registered users can re-register"""


def test_register_invalid():
    client = app.test_client()
    response = client.post(
        "/api/auth/register", json={"email": "bad@example.com", "password": "bad"}
    )
    assert response.status_code == 400


def test_register_invalid_email_format():
    client = app.test_client()
    response = client.post(
        "/api/auth/register",
        json={
            "email": "invalid-email-format",  # no @ should fail invalid
            "password": "validpassword123",
            "timezone": "UTC",
        },
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_email"}


def test_register_duplicate_email():
    client = app.test_client()
    with patch("main.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        # simulate dub key
        mock_db.users.insert_one.side_effect = DuplicateKeyError("duplicate")

        response = client.post(
            "/api/auth/register",
            json={
                "email": "existing@example.com",
                "password": "validpassword123",
                "timezone": "UTC",
            },
        )
        assert response.status_code == 409
        assert response.get_json() == {"error": "email_already_registered"}


""" test to check if registered users can login """


def test_valid_login():
    client = app.test_client()
    with patch("main.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.users.find_one.return_value = {
            "_id": "507f1f77bcf86cd799439011",
            "email": "test@example.com",
            "password_hash": generate_password_hash("nice123456"),
            "timezone": "UTC",
        }

        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "nice123456",
            },
        )
        assert response.status_code == 200


""" test to check if not registered people can login """


def test_invalid_login():
    client = app.test_client()
    with patch("main.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.users.find_one.return_value = None

        response = client.post(
            "/api/auth/login", json={"email": "idontexist@gg.com", "password": "lol"}
        )
    assert response.status_code == 401


""" test to check if the logout function is properly logging people out """


def test_logout():
    client = app.test_client()
    with patch("main.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.users.find_one.return_value = {
            "_id": "507f1f77bcf86cd799439011",
            "email": "test@example.com",
        }

        with client.session_transaction() as sess:
            sess["_user_id"] = "507f1f77bcf86cd799439011"

        response = client.post("/api/auth/logout")
        assert response.status_code == 200


""" test to check if logged me profile is correct """


def test_logged_in_me():
    client = app.test_client()
    with patch("flask_login.utils._get_user") as mock_current_user:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user.email = "test@example.com"
        mock_current_user.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_get_db.return_value.users.find_one.return_value = {"timezone": "UTC"}

            response = client.get("/api/auth/me")
            assert response.status_code == 200
            assert response.get_json()["logged_in"] is True


""" test to check invalid object id"""


def test_me_invalid_object_id():
    client = app.test_client()
    with patch("flask_login.utils._get_user") as mock_current_user:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "not-a-valid-object-id"
        mock_user.email = "test@example.com"
        mock_current_user.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            response = client.get("/api/auth/me")
            assert response.status_code == 200
            # user_doc becomes None and so timezone defaults to UTC
            assert response.get_json()["user"]["timezone"] == "UTC"


def test_update_me_success():
    client = app.test_client()
    with patch("flask_login.utils._get_user") as mock_current_user:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_current_user.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            response = client.patch("/api/auth/me", json={"timezone": "Asia/Tokyo"})
            assert response.status_code == 200
            assert response.get_json()["timezone"] == "Asia/Tokyo"
            mock_db.users.update_one.assert_called_once()


def test_update_me_missing_timezone():
    client = app.test_client()
    with patch("flask_login.utils._get_user") as mock_current_user:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_current_user.return_value = mock_user

        response = client.patch("/api/auth/me", json={"timezone": ""})
        assert response.status_code == 400
        assert response.get_json() == {"error": "missing_timezone"}


def test_update_me_invalid_id():
    client = app.test_client()
    with patch("flask_login.utils._get_user") as mock_current_user:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "invalid-id"
        mock_current_user.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            response = client.patch("/api/auth/me", json={"timezone": "UTC"})
            assert response.status_code == 400
            assert response.get_json() == {"error": "invalid_user_id"}


""" test to check if a not logged in user can see others profile """


def test_logged_out_me():
    client = app.test_client()
    response = client.get("/api/auth/me")
    assert response.get_json()["logged_in"] is False


def test_create_document():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.documents.insert_one.return_value.inserted_id = "doc123"

            response = client.post(
                "/api/documents/",
                json={
                    "doc_type": "passport",
                    "name": "my passport",
                    "expiry_date": "2030-01-12",
                },
            )

            assert response.status_code == 201


def test_delete_document():
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.documents.delete_one.return_value.deleted_count = 1

            response = client.delete("/api/documents/507f1f77bcf86cd799439012")
            assert response.status_code == 200


def test_renew_document():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # find doc to reinew
            mock_db.documents.find_one.return_value = {
                "_id": "507f1f77bcf86cd799439012",
                "user_id": "507f1f77bcf86cd799439011",
                "expiry_date": "2023-01-12",
            }

            response = client.post(
                "/api/documents/507f1f77bcf86cd799439012/renew",
                json={"new_expiry_date": "2030-01-12"},
            )

            assert response.status_code == 200


# helper funtion tests


def test_parse_date_loose():
    assert parse_date_loose(None) is None
    assert parse_date_loose("") is None
    assert parse_date_loose("   ") is None
    assert parse_date_loose("2023-01-01") == date(2023, 1, 1)
    assert parse_date_loose("2023-01-01T12:00:00") == date(2023, 1, 1)
    assert parse_date_loose("invalid") is None


def test_parse_date_strict():
    assert parse_date_strict(None) is None
    assert parse_date_strict("") is None
    assert parse_date_strict("2023-01-01") == date(2023, 1, 1)
    assert parse_date_strict("2023-01-01T12:00:00") is None  # len check
    assert parse_date_strict("invalid") is None


def test_compute_risk_level():
    assert compute_risk_level(-1, 5) == "CRITICAL"
    assert compute_risk_level(100, 5, lead_time_days=30) == "MEDIUM"  # > lead_time
    assert compute_risk_level(100, 1, lead_time_days=30) == "LOW"  # > lead_time

    # lead_time = 30. half = 15, quarter = 7.
    assert compute_risk_level(5, 5, 30) == "CRITICAL"  # <= quarter
    assert compute_risk_level(10, 5, 30) == "CRITICAL"  # <= half high importance
    assert compute_risk_level(10, 3, 30) == "HIGH"  # <= half low importance
    assert compute_risk_level(20, 5, 30) == "HIGH"  # > half high importance
    assert compute_risk_level(20, 3, 30) == "MEDIUM"  # > half low importance


def test_compute_status():
    assert compute_status(-1, 30) == "EXPIRED"
    assert compute_status(10, 30) == "IN_WINDOW"
    assert compute_status(40, 30) == "SAFE"


def test_build_name():
    assert build_name("passport", None) == "Passport"
    assert build_name("driver_license", "  ") == "Driver License"
    assert build_name("visa", "US") == "Visa (US)"


def test_coerce_lead_time():
    assert coerce_lead_time(None, 30) == 30
    assert coerce_lead_time("60", 30) == 60
    assert coerce_lead_time("invalid", 30) == 30
    assert coerce_lead_time(0, 30) == 1  # min 1
    assert coerce_lead_time(400, 30) == 365  # max 365


def test_normalize_doc_type():
    assert normalize_doc_type("Passport") == "passport"
    assert normalize_doc_type("Driver-License") == "driver_license"
    assert normalize_doc_type("unknown") == "other"
    assert normalize_doc_type(None) == "other"


def test_jsonify_value():
    assert _jsonify_value(date(2023, 1, 1)) == "2023-01-01"
    assert _jsonify_value([date(2023, 1, 1)]) == ["2023-01-01"]
    assert _jsonify_value({"d": date(2023, 1, 1)}) == {"d": "2023-01-01"}
    oid = ObjectId()
    assert _jsonify_value(oid) == str(oid)


def test_serialize_doc():
    assert _serialize_doc(None) is None
    oid = ObjectId()
    doc = {"_id": oid, "date": date(2023, 1, 1)}
    serialized = _serialize_doc(doc)
    assert serialized["id"] == str(oid)
    assert "_id" not in serialized
    assert serialized["date"] == "2023-01-01"


def test_renew_document_not_found():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.documents.find_one.return_value = None

            res = client.post(
                "/api/documents/507f1f77bcf86cd799439011/renew",
                json={"new_expiry_date": "2025-01-01"},
            )
            assert res.status_code == 404


def test_renew_document_success_with_options():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            doc_id = "507f1f77bcf86cd799439011"
            mock_db.documents.find_one.side_effect = [
                {
                    "_id": ObjectId(doc_id),
                    "user_id": ObjectId(mock_user.id),
                    "expiry_date": "2024-01-01",
                },  # first find
                {
                    "_id": ObjectId(doc_id),
                    "user_id": ObjectId(mock_user.id),
                    "expiry_date": "2025-01-01",
                },  # second find after update
            ]

            res = client.post(
                f"/api/documents/{doc_id}/renew",
                json={
                    "new_expiry_date": "2025-01-01",
                    "importance": "high",
                    "renewal_lead_time_days": 60,
                },
            )
            assert res.status_code == 200

            # verify update call
            mock_db.documents.update_one.assert_called_once()
            args = mock_db.documents.update_one.call_args
            update_doc = args[0][1]["$set"]
            assert update_doc["expiry_date"] == "2025-01-01"
            assert update_doc["importance"] == 4
            assert update_doc["renewal_lead_time_days"] == 60


def test_archive_unarchive():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            doc_id = "507f1f77bcf86cd799439011"

            # invalid ID
            res = client.post("/api/documents/invalid/archive")
            assert res.status_code == 400

            # not found
            mock_db.documents.update_one.return_value.matched_count = 0
            res = client.post(f"/api/documents/{doc_id}/archive")
            assert res.status_code == 404

            # success
            mock_db.documents.update_one.return_value.matched_count = 1
            mock_db.documents.find_one.return_value = {
                "_id": ObjectId(doc_id),
                "archived": True,
            }
            res = client.post(f"/api/documents/{doc_id}/archive")
            assert res.status_code == 200

            # unarchive invalid ID
            res = client.post("/api/documents/invalid/unarchive")
            assert res.status_code == 400

            # unarch not found
            mock_db.documents.update_one.return_value.matched_count = 0
            res = client.post(f"/api/documents/{doc_id}/unarchive")
            assert res.status_code == 404

            # unarchive success
            mock_db.documents.update_one.return_value.matched_count = 1
            mock_db.documents.find_one.return_value = {
                "_id": ObjectId(doc_id),
                "archived": False,
            }
            res = client.post(f"/api/documents/{doc_id}/unarchive")
            assert res.status_code == 200


def test_list_documents():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_db.users.find_one.return_value = {"timezone": "UTC"}

            # mock docs
            mock_db.documents.find.return_value = [
                {
                    "_id": ObjectId(),
                    "expiry_date": "2025-01-01",
                    "renewal_lead_time_days": 30,
                    "importance": 3,
                    "risk": "UNKNOWN",
                },
                {
                    "_id": ObjectId(),
                    "expiry_date": "2020-01-01",  # expired
                    "renewal_lead_time_days": 30,
                    "importance": 5,
                },
            ]

            res = client.get("/api/documents/")
            assert res.status_code == 200
            data = res.get_json()
            assert len(data) == 2
            # check sorting expired critical/expired should be first
            assert data[0]["expiry_status"] == "EXPIRED"


def test_create_document_validation():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            res = client.post(
                "/api/documents/",
                json={"doc_type": "passport", "expiry_date": "invalid"},
            )
            assert res.status_code == 400
            assert "invalid_expiry_date_format" in res.get_json()["error"]


def test_delete_document_errors():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # not found
            mock_db.documents.delete_one.return_value.deleted_count = 0
            res = client.delete("/api/documents/507f1f77bcf86cd799439011")
            assert res.status_code == 404

            # get exception
            mock_db.documents.delete_one.side_effect = Exception("DB Error")
            res = client.delete("/api/documents/507f1f77bcf86cd799439011")
            assert res.status_code == 400


def test_export_calendar():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # future date dock
            future_year = date.today().year + 2
            expiry_date = f"{future_year}-01-01"

            mock_db.documents.find.return_value.sort.return_value = [
                {
                    "_id": ObjectId(),
                    "name": "Doc 1",
                    "doc_type": "passport",
                    "expiry_date": expiry_date,
                    "renewal_lead_time_days": 30,
                    "notes": "Note 1",
                },
                {
                    "_id": ObjectId(),
                    "name": "Doc 2",
                    "doc_type": "visa",
                    "expiry_date": "invalid",  # should be skipped
                },
            ]

            res = client.get("/api/documents/calendar.ics")
            assert res.status_code == 200
            assert res.headers["Content-Type"] == "text/calendar; charset=utf-8"
            assert b"BEGIN:VCALENDAR" in res.data
            assert b"Doc 1 - Expires" in res.data
            assert b"Doc 1 - Renewal Reminder" in res.data


def test_user_get_empty_id():
    from auth_utils import User

    assert User.get(None) is None
    assert User.get("") is None


def test_user_get_invalid_object_id():
    from auth_utils import User

    assert User.get("not-a-valid-object-id") is None


def test_user_get_not_found():
    from auth_utils import User
    from bson import ObjectId

    with patch("main.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.users.find_one.return_value = None

        valid_oid = str(ObjectId())
        assert User.get(valid_oid) is None


def test_create_app_missing_secret():
    from main import create_app

    # Temporarily remove SECRET_KEY
    old_secret = os.environ.get("SECRET_KEY")
    if "SECRET_KEY" in os.environ:
        del os.environ["SECRET_KEY"]

    try:
        # Should raise ValueError
        try:
            create_app()
        except ValueError as e:
            assert "No SECRET_KEY set" in str(e)
        else:
            raise AssertionError("create_app() should have raised ValueError")
    finally:
        if old_secret:
            os.environ["SECRET_KEY"] = old_secret


def test_app_config_cookies():
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_blueprints_registered():
    assert "health" in app.blueprints
    assert "documents" in app.blueprints
    assert "auth" in app.blueprints

    rules = [str(r) for r in app.url_map.iter_rules()]
    assert any("/api/health" in r for r in rules)
    assert any("/api/auth" in r for r in rules)
    assert any("/api/documents" in r for r in rules)


def test_index_route():
    client = app.test_client()
    res = client.get("/")
    assert res.status_code == 200
    assert b"DocKeeper" in res.data


def test_get_mongo_client_is_cached(monkeypatch):
    import importlib
    import main

    # Reset cached client
    main._mongo_client = None

    fake_client = object()

    class FakeMongoClient:
        def __init__(self, uri):
            self.uri = uri

        def __getitem__(self, name):
            return {"db": name}

    monkeypatch.setattr(main, "MongoClient", lambda uri: FakeMongoClient(uri))

    c1 = main.get_mongo_client()
    c2 = main.get_mongo_client()

    assert c1 is c2  # proves the cache path ran


def test_get_db_uses_configured_db_name(monkeypatch):
    import main

    class FakeClient:
        def __getitem__(self, name):
            return f"DB:{name}"

    monkeypatch.setattr(main, "get_mongo_client", lambda: FakeClient())
    monkeypatch.setattr(main, "MONGO_DB_NAME", "dockeeper_test")

    assert main.get_db() == "DB:dockeeper_test"


def test_update_document_invalid_expiry():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.documents.find_one.return_value = {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "user_id": ObjectId("507f1f77bcf86cd799439011"),
            }

            res = client.patch(
                "/api/documents/507f1f77bcf86cd799439012",
                json={"expiry_date": "bad-date"},
            )
            assert res.status_code == 400
            assert "invalid_expiry_date_format" in res.get_json()["error"]


def test_update_document_change_expiry_side_effects():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            doc_id = "507f1f77bcf86cd799439012"
            old_doc = {
                "_id": ObjectId(doc_id),
                "user_id": ObjectId(mock_user.id),
                "expiry_date": "2024-01-01",
            }
            mock_db.documents.find_one.return_value = old_doc

            res = client.patch(
                f"/api/documents/{doc_id}", json={"expiry_date": "2025-01-01"}
            )
            assert res.status_code == 200

            assert mock_db.documents.update_one.call_count >= 2

            unset_call = [
                c
                for c in mock_db.documents.update_one.call_args_list
                if "$unset" in c[0][1]
            ]
            assert unset_call, "Should unset cached fields"

            set_call = [
                c
                for c in mock_db.documents.update_one.call_args_list
                if "$set" in c[0][1]
            ]
            assert set_call
            update_fields = set_call[-1][0][1]["$set"]
            assert update_fields["expiry_date"] == "2025-01-01"
            assert update_fields["archived"] is False


def test_update_document_regenerate_name():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            doc_id = "507f1f77bcf86cd799439012"
            old_doc = {
                "_id": ObjectId(doc_id),
                "user_id": ObjectId(mock_user.id),
                "doc_type": "passport",
                "label": "OldLabel",
                "name": "Manual Name",
            }
            mock_db.documents.find_one.return_value = old_doc

            # Update with empty name and new label
            res = client.patch(
                f"/api/documents/{doc_id}", json={"name": "", "label": "New"}
            )
            assert res.status_code == 200

            set_call = [
                c
                for c in mock_db.documents.update_one.call_args_list
                if "$set" in c[0][1]
            ]
            update_fields = set_call[-1][0][1]["$set"]
            assert update_fields["name"] == "Passport (New)"


def test_renew_document_validation_edges():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "507f1f77bcf86cd799439011"

    with patch("auth_utils.User.get") as mock_user_get:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user_get.return_value = mock_user

        with patch("main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            doc_id = "507f1f77bcf86cd799439012"

            # Invalid Date
            res = client.post(
                f"/api/documents/{doc_id}/renew", json={"new_expiry_date": "bad"}
            )
            assert res.status_code == 400

            # Invalid Importance Range
            res = client.post(
                f"/api/documents/{doc_id}/renew",
                json={"new_expiry_date": "2025-01-01", "importance": 10},
            )
            assert res.status_code == 400
            assert "invalid_importance" in res.get_json()["error"]

            # Invalid Lead Time
            res = client.post(
                f"/api/documents/{doc_id}/renew",
                json={"new_expiry_date": "2025-01-01", "renewal_lead_time_days": 0},
            )
            assert res.status_code == 400
            assert "invalid_lead_time_days" in res.get_json()["error"]


def test_parse_date_strict_invalid_real_date_hits_exception_branch():
    from routers.documents import parse_date_strict

    assert parse_date_strict("2024-02-30") is None


def test_compute_days_until_invalid_expiry_returns_none():
    from routers.documents import compute_days_until

    assert compute_days_until("not-a-date", "UTC") is None


def test_compute_days_until_invalid_timezone_falls_back_to_utc():
    from routers.documents import compute_days_until

    from datetime import datetime, timezone

    fixed = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed.astimezone(tz)

    with patch("routers.documents.datetime", FakeDateTime):
        assert compute_days_until("2024-01-03", "Not/AZone") == 2


def test_coerce_importance_covers_words_bounds_and_invalid():
    from routers.documents import coerce_importance

    assert coerce_importance(None, 3) == 3
    assert coerce_importance("", 3) == 3
    assert coerce_importance(" high ", 3) == 4
    assert coerce_importance("0", 3) == 1
    assert coerce_importance("6", 3) == 5
    assert coerce_importance("n/a", 3) == 3
