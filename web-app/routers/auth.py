from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from auth_utils import get_current_user_id

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _ensure_user_indexes(db) -> None:
    """Ensure indexes for the users collection."""
    db.users.create_index("email", unique=True)


@bp.post("/register")
def register():
    from main import get_db

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or "@" not in email:
        return jsonify({"error": "invalid_email"}), 400
    if len(password) < 8:
        return jsonify({"error": "password_too_short", "min_length": 8}), 400

    db = get_db()
    _ensure_user_indexes(db)

    user = {
        "email": email,
        "password_hash": generate_password_hash(password),
        "created_at": datetime.now(timezone.utc),
    }

    try:
        res = db.users.insert_one(user)
    except DuplicateKeyError:
        return jsonify({"error": "email_already_registered"}), 409

    session["user_id"] = str(res.inserted_id)
    return jsonify({"id": str(res.inserted_id), "email": email}), 201


@bp.post("/login")
def login():
    from main import get_db

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    db = get_db()
    user = db.users.find_one({"email": email})
    if not user or not check_password_hash(user.get("password_hash", ""), password):
        return jsonify({"error": "invalid_credentials"}), 401

    session["user_id"] = str(user["_id"])
    return jsonify({"id": str(user["_id"]), "email": user["email"]})


@bp.post("/logout")
def logout():
    session.pop("user_id", None)
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    from main import get_db

    uid = get_current_user_id()
    if not uid:
        return jsonify({"logged_in": False}), 200

    db = get_db()
    user = db.users.find_one({"_id": uid}, {"password_hash": 0})
    if not user:
        session.pop("user_id", None)
        return jsonify({"logged_in": False}), 200

    user["id"] = str(user["_id"])
    del user["_id"]
    return jsonify({"logged_in": True, "user": user})
