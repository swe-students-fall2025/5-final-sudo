from __future__ import annotations

import os
import json
import urllib.request

from bson import ObjectId
from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, user_id: str, email: str, is_verified: bool = False):
        self.id = user_id
        self.email = email
        self.is_verified = is_verified

    @staticmethod
    def get(user_id: str):
        from main import get_db

        if not user_id:
            return None
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None

        db = get_db()
        user_data = db.users.find_one({"_id": oid})
        if not user_data:
            return None

        return User(
            user_id=str(user_data["_id"]),
            email=user_data["email"],
            is_verified=bool(user_data.get("is_verified", False)),
        )


def send_verification_email(
    to_email: str, token: str, base_url: str | None = None
) -> None:
    """
    Verification email behavior:
    - If EMAIL_MODE=brevo: send via Brevo.
    - Otherwise: NO-OP (mock/dev = no verification emails).
    """
    email_mode = (os.environ.get("EMAIL_MODE") or "mock").strip().lower()
    if email_mode != "brevo":
        return

    base_url = (
        base_url or os.environ.get("APP_BASE_URL") or "http://localhost:8000"
    ).rstrip("/")
    verification_link = f"{base_url}/api/auth/verify?token={token}"

    api_key = os.environ.get("BREVO_API_KEY")
    sender_email = os.environ.get("BREVO_SENDER_EMAIL")
    sender_name = os.getenv("BREVO_SENDER_NAME", "DocKeeper")

    subject = "Verify your DocKeeper account"
    text_body = (
        "Hello,\n\n"
        "Please verify your email address to complete your registration.\n\n"
        f"Click here to verify: {verification_link}\n\n"
        "Link expires in 24 hours.\n"
    )

    if not api_key or not sender_email:
        print(
            "Error: BREVO_API_KEY or BREVO_SENDER_EMAIL not set for email sending.",
            flush=True,
        )
        return

    payload = {
        "sender": {"email": sender_email, "name": sender_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": text_body,
    }

    try:
        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "api-key": api_key,
                "accept": "application/json",
                "content-type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as response:
            response.read()
        print(f"Sent Brevo verification email to {to_email}", flush=True)
    except Exception as e:
        print(
            f"Failed to send Brevo verification email to {to_email}: {e}",
            flush=True,
        )


def send_password_reset_email(
    to_email: str, token: str, base_url: str | None = None
) -> None:
    """
    Password reset email behavior:
    - If EMAIL_MODE=brevo: send via Brevo.
    - Otherwise (mock/dev): print reset link to logs so local testing works.
    """
    base_url = (
        base_url or os.environ.get("APP_BASE_URL") or "http://localhost:8000"
    ).rstrip("/")
    reset_link = f"{base_url}/?reset_token={token}"

    email_mode = (os.environ.get("EMAIL_MODE") or "mock").strip().lower()

    subject = "Reset your DocKeeper password"
    text_body = (
        "Hello,\n\n"
        "We received a request to reset your DocKeeper password.\n\n"
        f"Reset your password here: {reset_link}\n\n"
        "If you did not request this, you can ignore this email.\n"
        "This link expires in 1 hour.\n"
    )

    if email_mode != "brevo":
        print(f"\n=== MOCK PASSWORD RESET EMAIL [To: {to_email}] ===", flush=True)
        print(f"Subject: {subject}", flush=True)
        print(f"Link: {reset_link}", flush=True)
        print("=================================================\n", flush=True)
        return

    api_key = os.environ.get("BREVO_API_KEY")
    sender_email = os.environ.get("BREVO_SENDER_EMAIL")
    sender_name = os.getenv("BREVO_SENDER_NAME", "DocKeeper")

    if not api_key or not sender_email:
        print(
            "Error: BREVO_API_KEY or BREVO_SENDER_EMAIL not set for email sending.",
            flush=True,
        )
        return

    payload = {
        "sender": {"email": sender_email, "name": sender_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": text_body,
    }

    try:
        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "api-key": api_key,
                "accept": "application/json",
                "content-type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as response:
            response.read()
        print(f"Sent Brevo password reset email to {to_email}", flush=True)
    except Exception as e:
        print(
            f"Failed to send Brevo password reset email to {to_email}: {e}",
            flush=True,
        )
