# web-app/routers/documents.py
from dataclasses import asdict
from typing import List

from flask import Blueprint, jsonify, request

from models import Document

bp = Blueprint("documents", __name__, url_prefix="/api/documents")

# In-memory storage for testing without database
_DOCUMENTS: List[Document] = []


@bp.get("/")
def list_documents():
    """Return all documents."""
    return jsonify([asdict(doc) for doc in _DOCUMENTS])


@bp.post("/")
def create_document():
    """Create a new document."""
    data = request.get_json() or {}

    new_id = len(_DOCUMENTS) + 1
    doc = Document(
        id=new_id,
        name=data.get("name", ""),
        category=data.get("category", ""),
        expiry_date=data.get("expiry_date", ""),
        importance=data.get("importance", 3),
        renewal_lead_time_days=data.get("renewal_lead_time_days", 30),
        notes=data.get("notes"),
    )
    _DOCUMENTS.append(doc)

    return jsonify(asdict(doc)), 201
