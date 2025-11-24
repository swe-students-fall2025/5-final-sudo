# web-app/routers/documents.py
from flask import Blueprint, jsonify, request
from bson import ObjectId

bp = Blueprint("documents", __name__, url_prefix="/api/documents")


def _serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable format."""
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc


@bp.get("/")
def list_documents():
    """Return all documents from MongoDB."""
    from main import get_db

    db = get_db()
    docs = list(db.documents.find())
    return jsonify([_serialize_doc(doc) for doc in docs])


@bp.post("/")
def create_document():
    """Create a new document in MongoDB."""
    from main import get_db

    data = request.get_json() or {}

    # Build document with defaults
    doc = {
        "name": data.get("name", ""),
        "category": data.get("category", ""),
        "expiry_date": data.get("expiry_date", ""),
        "importance": data.get("importance", 3),
        "renewal_lead_time_days": data.get("renewal_lead_time_days", 30),
        "notes": data.get("notes"),
    }

    db = get_db()
    result = db.documents.insert_one(doc)
    doc["_id"] = result.inserted_id

    return jsonify(_serialize_doc(doc)), 201
