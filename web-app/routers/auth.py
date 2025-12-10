from __future__ import annotations

import os
import secrets
import hashlib
from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request
from flask_login import login_user, logout_user, current_user, login_required
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash
from bson import ObjectId

from auth_utils import User, send_verification_email, send_password_reset_email

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _ensure_user_indexes(db) -> None:
    """Ensure indexes for the users collection."""
    db.users.create_index("email", unique=True)


def _email_mode() -> str:
    return (os.environ.get("EMAIL_MODE") or "mock").strip().lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@bp.post("/register")
def register():
    from main import get_db

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    timezone_val = (data.get("timezone") or "UTC").strip()

    if not email or "@" not in email:
        return jsonify({"error": "invalid_email"}), 400
    if len(password) < 8:
        return jsonify({"error": "password_too_short", "min_length": 8}), 400

    db = get_db()
    _ensure_user_indexes(db)

    mode = _email_mode()
    now = datetime.now(timezone.utc)

    if mode == "brevo":
        existing_user = db.users.find_one({"email": email})
        if existing_user and not existing_user.get("is_verified", False):
            token_expires = existing_user.get("verify_token_expires_at")
            if token_expires:
                if token_expires.tzinfo is None:
                    token_expires = token_expires.replace(tzinfo=timezone.utc)
                if token_expires < now:
                    db.users.delete_one({"_id": existing_user["_id"]})

    user_doc = {
        "email": email,
        "password_hash": generate_password_hash(password),
        "timezone": timezone_val,
        "created_at": now,
    }

    if mode == "brevo":
        user_doc.update(
            {
                "is_verified": False,
                "verify_token": secrets.token_urlsafe(32),
                "verify_token_expires_at": now + timedelta(hours=24),
            }
        )
    else:
        user_doc.update({"is_verified": True})

    try:
        res = db.users.insert_one(user_doc)
    except DuplicateKeyError:
        return jsonify({"error": "email_already_registered"}), 409

    if mode != "brevo":
        user = User(user_id=str(res.inserted_id), email=email, is_verified=True)
        login_user(user)
        return (
            jsonify({"id": user.id, "email": user.email, "timezone": timezone_val}),
            201,
        )

    base_url = (os.environ.get("APP_BASE_URL") or request.host_url).rstrip("/")
    send_verification_email(
        user_doc["email"],
        user_doc["verify_token"],
        base_url=base_url,
    )
    return (
        jsonify(
            {
                "message": (
                    "Verification required. Check your email to activate your account."
                )
            }
        ),
        201,
    )


@bp.get("/verify")
def verify():
    from main import get_db

    token = request.args.get("token")
    if not token:
        return "<h1>Missing Token</h1>", 400

    db = get_db()
    now = datetime.now(timezone.utc)

    user = db.users.find_one(
        {
            "verify_token": token,
            "verify_token_expires_at": {"$gt": now},
        }
    )
    if not user:
        return "<h1>Invalid or expired verification link</h1>", 400

    db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"is_verified": True},
            "$unset": {"verify_token": "", "verify_token_expires_at": ""},
        },
    )
    return (
        "<h1>Email Verified!</h1>"
        "<p>Your account is active. <a href='/'>Go to Dashboard</a></p>"
    )


@bp.post("/resend-verification")
def resend_verification():  # pylint: disable=too-many-return-statements
    from main import get_db

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "email_required"}), 400

    mode = _email_mode()
    db = get_db()

    if mode != "brevo":
        user = db.users.find_one({"email": email})
        if user and not user.get("is_verified", False):
            db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {"is_verified": True},
                    "$unset": {"verify_token": "", "verify_token_expires_at": ""},
                },
            )
        return (
            jsonify(
                {
                    "message": (
                        "Email verification is disabled in mock mode. "
                        "If this account exists, it is now active."
                    )
                }
            ),
            200,
        )

    user = db.users.find_one({"email": email})
    if not user:
        return (
            jsonify(
                {
                    "message": (
                        "If this account exists and is unverified, a new email has been sent."
                    )
                }
            ),
            200,
        )

    if user.get("is_verified"):
        return jsonify({"error": "already_verified"}), 400

    now = datetime.now(timezone.utc)
    last_resend = user.get("last_resend_at")
    if last_resend and last_resend.tzinfo is None:
        last_resend = last_resend.replace(tzinfo=timezone.utc)

    if last_resend and (now - last_resend).total_seconds() < 60:
        return (
            jsonify(
                {
                    "error": "rate_limit_exceeded",
                    "message": "Please wait 1 minute before retrying.",
                }
            ),
            429,
        )

    window_start = user.get("resend_window_start")
    count = user.get("resend_count", 0)

    if window_start and window_start.tzinfo is None:
        window_start = window_start.replace(tzinfo=timezone.utc)

    if not window_start or (now - window_start).total_seconds() > 3600:
        window_start = now
        count = 0

    if count >= 3:
        return (
            jsonify(
                {
                    "error": "rate_limit_exceeded",
                    "message": "Too many attempts. Please try again in an hour.",
                }
            ),
            429,
        )

    new_token = secrets.token_urlsafe(32)
    new_expiry = now + timedelta(hours=24)

    db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "verify_token": new_token,
                "verify_token_expires_at": new_expiry,
                "last_resend_at": now,
                "resend_window_start": window_start,
                "resend_count": count + 1,
            }
        },
    )

    base_url = (os.environ.get("APP_BASE_URL") or request.host_url).rstrip("/")
    send_verification_email(email, new_token, base_url=base_url)
    return jsonify({"message": "Verification email resent."}), 200


@bp.post("/forgot-password")
def forgot_password():
    """
    Secure password-reset request:
    - Always returns a generic success message (no user enumeration).
    - If user exists and rate limits allow: store hashed reset token + expiry, email link.
    """
    from main import get_db

    message = "If this account exists, a password reset link has been sent."

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    db = get_db()

    user = None
    if email and "@" in email:
        user = db.users.find_one({"email": email})

    if user:
        now = datetime.now(timezone.utc)

        # Rate limit (60s cooldown + max 3/hour)
        last_sent = user.get("reset_last_sent_at")
        if last_sent and last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)

        window_start = user.get("reset_window_start")
        count = user.get("reset_count", 0)

        if window_start and window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=timezone.utc)

        cooldown_ok = not last_sent or (now - last_sent).total_seconds() >= 60

        if not window_start or (now - window_start).total_seconds() > 3600:
            window_start = now
            count = 0

        hourly_ok = count < 3

        if cooldown_ok and hourly_ok:
            raw_token = secrets.token_urlsafe(32)
            token_hash = _hash_token(raw_token)
            expires = now + timedelta(hours=1)

            db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "reset_token_hash": token_hash,
                        "reset_token_expires_at": expires,
                        "reset_last_sent_at": now,
                        "reset_window_start": window_start,
                        "reset_count": count + 1,
                    }
                },
            )

            base_url = (os.environ.get("APP_BASE_URL") or request.host_url).rstrip("/")
            send_password_reset_email(email, raw_token, base_url=base_url)

    return jsonify({"message": message}), 200


@bp.post("/reset-password")
def reset_password():
    """
    Completes password reset using token:
    - Validates token + expiry.
    - Sets new password.
    - Marks verified (proves email control).
    - Clears verification + reset tokens.
    - Logs user in.
    """
    from main import get_db

    data = request.get_json() or {}
    token = (data.get("token") or "").strip()
    password = data.get("password") or ""
    password2 = data.get("password2") or ""

    if not token:
        return jsonify({"error": "missing_token"}), 400
    if len(password) < 8:
        return jsonify({"error": "password_too_short", "min_length": 8}), 400
    if password != password2:
        return jsonify({"error": "passwords_do_not_match"}), 400

    db = get_db()
    now = datetime.now(timezone.utc)
    token_hash = _hash_token(token)

    user = db.users.find_one(
        {
            "reset_token_hash": token_hash,
            "reset_token_expires_at": {"$gt": now},
        }
    )
    if not user:
        return jsonify({"error": "invalid_or_expired_token"}), 400

    db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_hash": generate_password_hash(password),
                "is_verified": True,
            },
            "$unset": {
                "reset_token_hash": "",
                "reset_token_expires_at": "",
                # If they reset password, they proved email ownership:
                "verify_token": "",
                "verify_token_expires_at": "",
            },
        },
    )

    user_obj = User(user_id=str(user["_id"]), email=user["email"], is_verified=True)
    login_user(user_obj)

    return (
        jsonify(
            {
                "id": user_obj.id,
                "email": user_obj.email,
                "timezone": user.get("timezone", "UTC"),
            }
        ),
        200,
    )


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

    mode = _email_mode()

    if mode == "brevo" and not user_doc.get("is_verified", False):
        return jsonify({"error": "email_not_verified"}), 403

    if mode != "brevo" and not user_doc.get("is_verified", False):
        db.users.update_one(
            {"_id": user_doc["_id"]},
            {
                "$set": {"is_verified": True},
                "$unset": {"verify_token": "", "verify_token_expires_at": ""},
            },
        )
        user_doc["is_verified"] = True

    user = User(
        user_id=str(user_doc["_id"]),
        email=user_doc["email"],
        is_verified=bool(user_doc.get("is_verified", False)),
    )
    login_user(user)

    return jsonify(
        {
            "id": user.id,
            "email": user.email,
            "timezone": user_doc.get("timezone", "UTC"),
        }
    )


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    if current_user.is_authenticated:
        from main import get_db

        db = get_db()
        try:
            uid = ObjectId(current_user.id)
            user_doc = db.users.find_one({"_id": uid})
        except Exception:
            user_doc = None

        tz = (user_doc.get("timezone") if user_doc else None) or "UTC"
        return jsonify(
            {
                "logged_in": True,
                "user": {
                    "id": current_user.id,
                    "email": current_user.email,
                    "timezone": tz,
                },
            }
        )

    return jsonify({"logged_in": False}), 200


@bp.patch("/me")
@login_required
def update_me():
    from main import get_db

    data = request.get_json() or {}
    timezone_val = (data.get("timezone") or "").strip()
    if not timezone_val:
        return jsonify({"error": "missing_timezone"}), 400

    db = get_db()
    try:
        uid = ObjectId(current_user.id)
    except Exception:
        return jsonify({"error": "invalid_user_id"}), 400

    db.users.update_one({"_id": uid}, {"$set": {"timezone": timezone_val}})
    return jsonify({"message": "updated", "timezone": timezone_val}), 200
