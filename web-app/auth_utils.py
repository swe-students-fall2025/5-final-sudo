from __future__ import annotations

from functools import wraps
from typing import Optional

from bson import ObjectId
from flask import jsonify, session, g


def get_current_user_id() -> Optional[ObjectId]:
    """Return the logged-in user's ObjectId, or None if not logged in/invalid."""
    raw = session.get("user_id")
    if not raw:
        return None
    try:
        return ObjectId(str(raw))
    except Exception:
        return None


def login_required(fn):
    """Require a valid logged-in user and attach g.user_id (ObjectId)."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        uid = get_current_user_id()
        if not uid:
            # Clear bad/stale session value if present
            session.pop("user_id", None)
            return jsonify({"error": "auth_required"}), 401
        g.user_id = uid
        return fn(*args, **kwargs)

    return wrapper
