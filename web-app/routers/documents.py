# web-app/routers/documents.py
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response
from bson import ObjectId
from flask_login import login_required, current_user
from icalendar import Calendar, Event, Alarm

bp = Blueprint("documents", __name__, url_prefix="/api/documents")

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


def _serialize_doc(doc):
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    if "user_id" in doc and isinstance(doc["user_id"], ObjectId):
        doc["user_id"] = str(doc["user_id"])
    return doc


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

    docs = list(db.documents.find({"user_id": uid}).sort("expiry_date", 1))
    return jsonify([_serialize_doc(doc) for doc in docs])


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

    # Fetch all documents for the user
    docs = list(db.documents.find({"user_id": uid}).sort("expiry_date", 1))

    # Create iCalendar
    cal = Calendar()
    cal.add("prodid", "-//DocKeeper//Document Expiry Tracker//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("X-WR-CALNAME", "DocKeeper Document Expiry Calendar")
    cal.add("X-WR-CALDESC", "Document expiry dates and reminders from DocKeeper")

    for doc in docs:
        expiry_date_str = doc.get("expiry_date", "")
        if not expiry_date_str:
            continue

        try:
            # Parse expiry date (assuming ISO format YYYY-MM-DD)
            expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            # Skip documents with invalid dates
            continue

        try:
            name = doc.get("name", "Document")
            doc_type = doc.get("doc_type", "document")
            lead_time_days = doc.get("renewal_lead_time_days", 30)
            notes = doc.get("notes", "")

            # Event 1: Expiry Date (required)
            expiry_event = Event()
            expiry_event.add("summary", f"{name} - Expires")
            expiry_event.add("description", f"Document: {name}\nType: {doc_type}\n{notes}".strip())
            expiry_event.add("dtstart", expiry_date.date())
            expiry_event.add("dtend", (expiry_date + timedelta(days=1)).date())
            expiry_event.add("dtstamp", datetime.utcnow())
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
                reminder_date = expiry_date - timedelta(days=lead_time_days)
                # Only add reminder event if it's in the future
                if reminder_date > datetime.now():
                    reminder_event = Event()
                    reminder_event.add("summary", f"{name} - Renewal Reminder")
                    reminder_event.add(
                        "description",
                        f"Time to renew: {name}\nType: {doc_type}\nExpires: {expiry_date_str}\n{notes}".strip()
                    )
                    reminder_event.add("dtstart", reminder_date.date())
                    reminder_event.add("dtend", (reminder_date + timedelta(days=1)).date())
                    reminder_event.add("dtstamp", datetime.utcnow())
                    reminder_event.add("uid", f"dockeeper-reminder-{doc.get('_id')}@dockeeper")
                    reminder_event.add("status", "CONFIRMED")
                    reminder_event.add("transp", "OPAQUE")
                    # Set alarm for reminder
                    reminder_alarm = Alarm()
                    reminder_alarm.add("action", "DISPLAY")
                    reminder_alarm.add("description", f"Reminder: {name} expires in {lead_time_days} days")
                    reminder_alarm.add("trigger", timedelta(hours=-2))  # 2 hours before reminder date
                    reminder_event.add_component(reminder_alarm)
                    cal.add_component(reminder_event)

        except Exception:
            # Skip documents that cause errors
            continue

    # Return as .ics file
    response = Response(cal.to_ical(), mimetype="text/calendar")
    response.headers["Content-Disposition"] = "attachment; filename=dockeeper-calendar.ics"
    return response
