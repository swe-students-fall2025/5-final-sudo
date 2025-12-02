from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import login_user, logout_user, current_user, login_required
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from auth_utils import User

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

    user_doc = {
        "email": email,
        "password_hash": generate_password_hash(password),
        "created_at": datetime.now(timezone.utc),
    }

    try:
        res = db.users.insert_one(user_doc)
    except DuplicateKeyError:
        return jsonify({"error": "email_already_registered"}), 409

    user = User(user_id=str(res.inserted_id), email=email)
    login_user(user)

    return jsonify({"id": user.id, "email": user.email}), 201


@bp.post("/login")
def login():
    from main import get_db

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    db = get_db()
    user_doc = db.users.find_one({"email": email})
    if not user_doc or not check_password_hash(
        user_doc.get("password_hash", ""), password
    ):
        return jsonify({"error": "invalid_credentials"}), 401

    user = User(user_id=str(user_doc["_id"]), email=user_doc["email"])
    login_user(user)

    return jsonify({"id": user.id, "email": user.email})


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    if current_user.is_authenticated:
        return jsonify(
            {
                "logged_in": True,
                "user": {"id": current_user.id, "email": current_user.email},
            }
        )
    return jsonify({"logged_in": False}), 200
