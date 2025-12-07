# web-app/routers/documents.py
from datetime import datetime, timedelta, date, timezone
from flask import Blueprint, jsonify, request, Response
from bson import ObjectId
from flask_login import login_required, current_user
from icalendar import Calendar, Event, Alarm

bp = Blueprint("documents", __name__, url_prefix="/api/documents")

RISK_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0, None: 0}
STATUS_RANK = {"EXPIRED": 3, "IN_WINDOW": 2, "SAFE": 1, "UNKNOWN": 0}


def parse_date_loose(value: str) -> date | None:
    """Loose parser for reading existing dates from DB (accepts YYYY-MM-DD or YYYY-MM-DDTHH...)."""
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])  # allows YYYY-MM-DDTHH...
    except Exception:
        return None


def parse_date_strict(value: str) -> date | None:
    """Strict validator for write operations (only accepts YYYY-MM-DD)"""
    if not value:
        return None
    s = str(value).strip()
    if len(s) != 10:
        return None
    try:
        return date.fromisoformat(s)  # only accepts YYYY-MM-DD
    except Exception:
        return None


def compute_days_until(expiry_value: str) -> int | None:
    expiry = parse_date_loose(expiry_value)
    if not expiry:
        return None
    return (expiry - date.today()).days


def compute_status(days_until: int, lead_time_days: int) -> str:
    if days_until < 0:
        return "EXPIRED"
    if days_until <= lead_time_days:
        return "IN_WINDOW"
    return "SAFE"


DOC_TEMPLATES = {
    "passport": {"category": "ID", "importance": 5, "lead_time": 180},
    "visa": {"category": "ID", "importance": 5, "lead_time": 120},
    "driver_license": {"category": "ID", "importance": 4, "lead_time": 90},
    "permit": {"category": "Permit", "importance": 3, "lead_time": 30},
    "car_registration": {"category": "Vehicle", "importance": 4, "lead_time": 30},
    "insurance": {"category": "Finance", "importance": 4, "lead_time": 30},
    "lease": {"category": "Housing", "importance": 5, "lead_time": 90},
    "subscription": {"category": "Subscription", "importance": 2, "lead_time": 7},
    "warranty": {"category": "Warranty", "importance": 2, "lead_time": 30},
    "license": {"category": "ID", "importance": 4, "lead_time": 90},
    "membership": {"category": "Subscription", "importance": 2, "lead_time": 30},
    "certification": {"category": "ID", "importance": 4, "lead_time": 60},
    "other": {"category": "Other", "importance": 3, "lead_time": 30},  # default only
}

IMPORTANCE_WORDS = {
    "low": 2,
    "medium": 3,
    "high": 4,
    "critical": 5,
}


def normalize_doc_type(value: str) -> str:
    v = (value or "").strip().lower()
    v = v.replace(" ", "_").replace("-", "_")
    return v if v in DOC_TEMPLATES else "other"


def build_name(doc_type: str, label: str | None) -> str:
    pretty = doc_type.replace("_", " ").title()
    label = (label or "").strip()
    return f"{pretty} ({label})" if label else pretty


def _jsonify_value(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, list):
        return [_jsonify_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonify_value(x) for k, x in v.items()}
    return v


def _serialize_doc(doc):
    if not doc:
        return doc
    doc = dict(doc)
    oid = doc.pop("_id", None)
    if oid is not None:
        doc["id"] = str(oid)
    return {k: _jsonify_value(v) for k, v in doc.items()}


@bp.post("/<doc_id>/renew")
@login_required
# pylint: disable=too-many-return-statements
def renew_document(doc_id):
    """Body: { new_expiry_date: 'YYYY-MM-DD', importance?: int, renewal_lead_time_days?: int }"""
    from main import get_db

    db = get_db()
    uid = ObjectId(current_user.id)
    payload = request.get_json(silent=True) or {}

    # Validate inputs (single error return)
    new_expiry = (payload.get("new_expiry_date") or "").strip()
    if not parse_date_strict(new_expiry):
        return (
            jsonify(
                {"error": "invalid_new_expiry_date_format", "expected": "YYYY-MM-DD"}
            ),
            400,
        )

    importance_raw = payload.get("importance")
    lead_raw = payload.get("renewal_lead_time_days")

    importance = None
    lead_time = None

    # Validate optional overrides
    if importance_raw is not None and importance_raw != "":
        try:
            if (
                isinstance(importance_raw, str)
                and importance_raw.strip().lower() in IMPORTANCE_WORDS
            ):
                importance = IMPORTANCE_WORDS[importance_raw.strip().lower()]
            else:
                importance = int(importance_raw)
            if importance < 1 or importance > 5:
                return jsonify({"error": "invalid_importance", "range": [1, 5]}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "invalid_importance_type"}), 400

    if lead_raw is not None and lead_raw != "":
        try:
            lead_time = int(lead_raw)
            if lead_time < 1:
                return jsonify({"error": "invalid_lead_time_days", "min": 1}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "invalid_lead_time_days_type"}), 400

    try:
        oid = ObjectId(doc_id)
    except Exception:
        return jsonify({"error": "invalid_id"}), 400

    doc = db.documents.find_one({"_id": oid, "user_id": uid})
    if not doc:
        return jsonify({"error": "not_found"}), 404

    update_fields = {
        "expiry_date": new_expiry,
        "archived": False,
        "updated_at": datetime.now(timezone.utc),
    }
    if importance is not None:
        update_fields["importance"] = importance
    if lead_time is not None:
        update_fields["renewal_lead_time_days"] = lead_time

    history_entry = {
        "old_expiry_date": doc.get("expiry_date"),
        "new_expiry_date": new_expiry,
        "renewed_at": datetime.now(timezone.utc),
    }

    db.documents.update_one(
        {"_id": oid, "user_id": uid},
        {
            "$set": update_fields,
            "$push": {"renewal_history": history_entry},
            "$unset": {
                "archived_at": "",
                "last_risk": "",
                "last_days_until": "",
                "last_checked_at": "",
            },
        },
    )

    updated = db.documents.find_one({"_id": oid, "user_id": uid})
    return jsonify(_serialize_doc(updated)), 200


@bp.patch("/<doc_id>")
@login_required
def update_document(doc_id):
    """
    General purpose update.
    Can update details like label, notes AND/OR renewal fields like expiry, importance, lead.
    If 'expiry_date' is changed, it treats it as a renewal.
    """
    from main import get_db

    db = get_db()
    uid = ObjectId(current_user.id)
    payload = request.get_json(silent=True) or {}

    try:
        oid = ObjectId(doc_id)
    except Exception:
        return jsonify({"error": "invalid_id"}), 400

    doc = db.documents.find_one({"_id": oid, "user_id": uid})
    if not doc:
        return jsonify({"error": "not_found"}), 404

    update_fields = {
        "updated_at": datetime.now(timezone.utc),
    }

    # Handle Simple Text Fields
    if "label" in payload:
        update_fields["label"] = (payload["label"] or "").strip() or None

    if "notes" in payload:
        update_fields["notes"] = (payload["notes"] or "").strip()

    if "name" in payload:
        name_val = (payload["name"] or "").strip()
        if not name_val:
            # Fallback: regenerate from type + label
            new_label = (
                update_fields["label"] if "label" in update_fields else doc.get("label")
            )
            name_val = build_name(doc.get("doc_type"), new_label)
        update_fields["name"] = name_val
    new_expiry = (payload.get("expiry_date") or "").strip()
    if new_expiry:
        if not parse_date_strict(new_expiry):
            return (
                jsonify(
                    {"error": "invalid_expiry_date_format", "expected": "YYYY-MM-DD"}
                ),
                400,
            )

        # Check if it's actually different
        if new_expiry != doc.get("expiry_date"):
            update_fields["expiry_date"] = new_expiry
            update_fields["archived"] = False

            history_entry = {
                "old_expiry_date": doc.get("expiry_date"),
                "new_expiry_date": new_expiry,
                "renewed_at": datetime.now(timezone.utc),
            }

            db.documents.update_one(
                {"_id": oid}, {"$push": {"renewal_history": history_entry}}
            )

            db.documents.update_one(
                {"_id": oid},
                {
                    "$unset": {
                        "archived_at": "",
                        "last_risk": "",
                        "last_days_until": "",
                        "last_checked_at": "",
                    }
                },
            )

    if "importance" in payload:
        importance_raw = payload["importance"]
        imp = coerce_importance(importance_raw, doc.get("importance", 3))
        update_fields["importance"] = imp

    if "renewal_lead_time_days" in payload:
        lead_raw = payload["renewal_lead_time_days"]
        lead = coerce_lead_time(lead_raw, doc.get("renewal_lead_time_days", 30))
        update_fields["renewal_lead_time_days"] = lead

    # Execute Set
    db.documents.update_one({"_id": oid, "user_id": uid}, {"$set": update_fields})

    updated = db.documents.find_one({"_id": oid, "user_id": uid})
    return jsonify(_serialize_doc(updated)), 200


@bp.post("/<doc_id>/archive")
@login_required
def archive_document(doc_id):
    """Archive a document (set status=archived, archived_at=now)."""
    from main import get_db

    db = get_db()
    uid = ObjectId(current_user.id)

    try:
        oid = ObjectId(doc_id)
    except Exception:
        return jsonify({"error": "invalid_id"}), 400

    res = db.documents.update_one(
        {"_id": oid, "user_id": uid},
        {"$set": {"archived": True, "archived_at": datetime.now(timezone.utc)}},
    )
    if res.matched_count == 0:
        return jsonify({"error": "not_found"}), 404

    doc = db.documents.find_one({"_id": oid, "user_id": uid})
    return jsonify(_serialize_doc(doc)), 200


@bp.post("/<doc_id>/unarchive")
@login_required
def unarchive_document(doc_id):
    """Unarchive a document (set status=active, clear archived_at)."""
    from main import get_db

    db = get_db()
    uid = ObjectId(current_user.id)

    try:
        oid = ObjectId(doc_id)
    except Exception:
        return jsonify({"error": "invalid_id"}), 400

    res = db.documents.update_one(
        {"_id": oid, "user_id": uid},
        {"$set": {"archived": False}, "$unset": {"archived_at": ""}},
    )
    if res.matched_count == 0:
        return jsonify({"error": "not_found"}), 404

    doc = db.documents.find_one({"_id": oid, "user_id": uid})
    return jsonify(_serialize_doc(doc)), 200


def coerce_importance(value, default: int) -> int:
    if value is None or value == "":
        return default
    # allow strings like "high"
    if isinstance(value, str):
        v = value.strip().lower()
        if v in IMPORTANCE_WORDS:
            return IMPORTANCE_WORDS[v]
    try:
        n = int(value)
        return min(5, max(1, n))
    except Exception:
        return default


def coerce_lead_time(value, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        n = int(value)
        # keep sane bounds; adjust if you want
        return min(365, max(1, n))
    except Exception:
        return default


@bp.get("/")
@login_required
def list_documents():
    from main import get_db

    db = get_db()
    uid = ObjectId(current_user.id)

    include_archived = (request.args.get("include_archived") or "").strip().lower()
    query = {"user_id": uid}
    if include_archived not in ("1", "true", "yes"):
        query["archived"] = {"$ne": True}
    docs = list(db.documents.find(query))

    out = []
    for d in docs:
        lead = int(d.get("renewal_lead_time_days") or 0)

        # prefer worker value if present, else compute quickly
        days_until = d.get("last_days_until")
        if days_until is None:
            days_until = compute_days_until(d.get("expiry_date", ""))

        if days_until is None:
            expiry_status = "UNKNOWN"
        else:
            expiry_status = compute_status(int(days_until), lead)

        risk = d.get("last_risk") or "UNKNOWN"

        d["days_until"] = days_until
        d["expiry_status"] = expiry_status
        d["risk"] = risk

        out.append(_serialize_doc(d))

    # worst-first default ordering
    def sort_key(doc):
        risk_rank = RISK_RANK.get(doc.get("risk"), 0)
        status_rank = STATUS_RANK.get(doc.get("expiry_status"), 0)
        days = doc.get("days_until")
        days_sort = days if isinstance(days, int) else 10**9
        return (-risk_rank, -status_rank, days_sort)

    out.sort(key=sort_key)
    return jsonify(out)


@bp.post("/")
@login_required
def create_document():
    from main import get_db

    data = request.get_json() or {}

    doc_type = normalize_doc_type(
        data.get("doc_type") or data.get("type") or data.get("category")
    )
    label = data.get("label")
    expiry_date = (data.get("expiry_date") or "").strip()
    notes = data.get("notes")

    # Validate expiry_date format
    if expiry_date and not parse_date_strict(expiry_date):
        return (
            jsonify({"error": "invalid_expiry_date_format", "expected": "YYYY-MM-DD"}),
            400,
        )

    template = DOC_TEMPLATES[doc_type]

    # Overrides (optional for all types, especially important for "other")
    importance = coerce_importance(data.get("importance"), template["importance"])
    lead_time = coerce_lead_time(
        data.get("renewal_lead_time_days"), template["lead_time"]
    )

    # Backward compat: prefer provided name, else generate from type/label
    name = (data.get("name") or "").strip() or build_name(doc_type, label)

    uid = ObjectId(current_user.id)

    doc = {
        "doc_type": doc_type,
        "label": (label or "").strip() or None,
        "name": name,
        "category": template["category"],
        "expiry_date": expiry_date,
        "importance": importance,
        "renewal_lead_time_days": lead_time,
        "notes": notes,
        # Ownership
        "user_id": uid,
        # Lifecycle state
        "archived": False,
        "archived_at": None,
        # Renewal history audit trail
        "renewal_history": [],
        # Optional: helps the UI show “customized” badge if overrides were used
        "custom_overrides": {
            "importance": data.get("importance") is not None
            and data.get("importance") != "",
            "lead_time": data.get("renewal_lead_time_days") is not None
            and data.get("renewal_lead_time_days") != "",
        },
    }

    db = get_db()
    result = db.documents.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify(_serialize_doc(doc)), 201


@bp.delete("/<doc_id>")
@login_required
def delete_document(doc_id):
    """Delete a document by ID."""
    from main import get_db

    try:
        uid = ObjectId(current_user.id)
        db = get_db()
        result = db.documents.delete_one({"_id": ObjectId(doc_id), "user_id": uid})

        if result.deleted_count == 0:
            return jsonify({"error": "Document not found"}), 404

        return jsonify({"message": "Document deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.get("/calendar.ics")
@login_required
def export_calendar():
    """Export all user documents as an iCalendar (.ics) file.

    Creates two events per document:
    1. Expiry date event (required)
    2. Reminder start date event (expiry_date - renewal_lead_time_days, optional)
    """
    from main import get_db

    db = get_db()
    uid = ObjectId(current_user.id)

    # Fetch documents for the user (default active-only, opt-in archived)
    include_archived = (request.args.get("include_archived") or "").strip().lower()
    cal_query = {"user_id": uid}
    if include_archived not in ("1", "true", "yes"):
        cal_query["archived"] = {"$ne": True}
    docs = list(db.documents.find(cal_query).sort("expiry_date", 1))

    # Create iCalendar
    cal = Calendar()
    cal.add("prodid", "-//DocKeeper//Document Expiry Tracker//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("X-WR-CALNAME", "DocKeeper Document Expiry Calendar")
    cal.add("X-WR-CALDESC", "Document expiry dates and reminders from DocKeeper")

    for doc in docs:
        expiry = parse_date_loose(doc.get("expiry_date", ""))
        if not expiry:
            continue

        try:
            name = doc.get("name", "Document")
            doc_type = doc.get("doc_type", "document")
            lead_time_days = int(doc.get("renewal_lead_time_days") or 0)
            notes = doc.get("notes", "")

            # Event 1: Expiry Date (required)
            expiry_event = Event()
            expiry_event.add("summary", f"{name} - Expires")
            expiry_event.add(
                "description", f"Document: {name}\nType: {doc_type}\n{notes}".strip()
            )
            expiry_event.add("dtstart", expiry)
            expiry_event.add("dtend", expiry + timedelta(days=1))
            expiry_event.add("dtstamp", datetime.now(timezone.utc))
            expiry_event.add("uid", f"dockeeper-expiry-{doc.get('_id')}@dockeeper")
            expiry_event.add("status", "CONFIRMED")
            expiry_event.add("transp", "OPAQUE")
            # Set alarm/reminder for expiry date
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", f"{name} expires today!")
            alarm.add("trigger", timedelta(hours=-24))  # 24 hours before
            expiry_event.add_component(alarm)
            cal.add_component(expiry_event)

            # Event 2: Reminder Start Date (optional, if lead_time_days > 0)
            if lead_time_days > 0:
                reminder_day = expiry - timedelta(days=lead_time_days)
                # Only add reminder event if it's in the future
                if reminder_day >= date.today():
                    reminder_event = Event()
                    reminder_event.add("summary", f"{name} - Renewal Reminder")
                    desc = (
                        f"Time to renew: {name}\nType: {doc_type}\n"
                        f"Expires: {expiry.isoformat()}\n{notes}"
                    ).strip()
                    reminder_event.add("description", desc)
                    reminder_event.add("dtstart", reminder_day)
                    reminder_event.add("dtend", reminder_day + timedelta(days=1))
                    reminder_event.add("dtstamp", datetime.now(timezone.utc))
                    reminder_event.add(
                        "uid", f"dockeeper-reminder-{doc.get('_id')}@dockeeper"
                    )
                    reminder_event.add("status", "CONFIRMED")
                    reminder_event.add("transp", "OPAQUE")
                    # Set alarm for reminder
                    reminder_alarm = Alarm()
                    reminder_alarm.add("action", "DISPLAY")
                    reminder_alarm.add(
                        "description",
                        f"Reminder: {name} expires in {lead_time_days} days",
                    )
                    reminder_alarm.add(
                        "trigger", timedelta(hours=-2)
                    )  # 2 hours before reminder date
                    reminder_event.add_component(reminder_alarm)
                    cal.add_component(reminder_event)

        except Exception:
            # Skip documents that cause errors
            continue

    # Return as .ics file
    response = Response(cal.to_ical(), mimetype="text/calendar")
    response.headers["Content-Disposition"] = (
        "attachment; filename=dockeeper-calendar.ics"
    )
    return response
