# web-app/routers/documents.py
from flask import Blueprint, jsonify, request
from bson import ObjectId

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
def list_documents():
    from main import get_db

    db = get_db()
    docs = list(db.documents.find().sort("expiry_date", 1))
    return jsonify([_serialize_doc(doc) for doc in docs])


@bp.post("/")
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

    doc = {
        "doc_type": doc_type,
        "label": (label or "").strip() or None,
        "name": name,
        "category": template["category"],
        "expiry_date": expiry_date,
        "importance": importance,
        "renewal_lead_time_days": lead_time,
        "notes": notes,
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
def delete_document(doc_id):
    """Delete a document by ID."""
    from main import get_db

    try:
        db = get_db()
        result = db.documents.delete_one({"_id": ObjectId(doc_id)})

        if result.deleted_count == 0:
            return jsonify({"error": "Document not found"}), 404

        return jsonify({"message": "Document deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
