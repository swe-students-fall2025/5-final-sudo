import os
import time
import json
import urllib.request
import urllib.error
from datetime import datetime, date, timezone
from typing import Optional

from bson import ObjectId
from pymongo import MongoClient
from pymongo.database import Database

from logic import compute_risk_level

SERVICE_NAME = "DocKeeper Expiry Reminder Service"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "dockeeper")
REMINDER_INTERVAL_SECONDS = int(os.getenv("REMINDER_INTERVAL_SECONDS", "60"))

_client: Optional[MongoClient] = None

DOC_DEFAULTS = {
    "passport": {"importance": 5, "lead": 180},
    "visa": {"importance": 5, "lead": 120},
    "driver_license": {"importance": 4, "lead": 90},
    "permit": {"importance": 3, "lead": 30},
    "car_registration": {"importance": 4, "lead": 30},
    "insurance": {"importance": 4, "lead": 30},
    "lease": {"importance": 5, "lead": 90},
    "subscription": {"importance": 2, "lead": 7},
    "warranty": {"importance": 2, "lead": 30},
    "license": {"importance": 4, "lead": 90},
    "membership": {"importance": 2, "lead": 7},
    "credit_card": {"importance": 5, "lead": 30},
    "medical_record": {"importance": 4, "lead": 60},
    "certification": {"importance": 4, "lead": 60},
    "other": {"importance": 3, "lead": 30},
}


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db() -> Database:
    return get_mongo_client()[MONGO_DB_NAME]


def close_db_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def parse_expiry_date(expiry_value) -> Optional[date]:
    if not expiry_value:
        return None

    s = str(expiry_value).strip()
    if not s:
        return None

    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass

    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


def normalize_doc_type(value: str) -> str:
    v = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return v if v in DOC_DEFAULTS else "other"


def get_importance(doc) -> int:
    # Prefer stored importance if valid
    try:
        imp = int(doc.get("importance"))
        if 1 <= imp <= 5:
            return imp
    except Exception:
        pass

    # Fallback to Service Default (Safe Source of Truth)
    doc_type = normalize_doc_type(
        doc.get("doc_type") or doc.get("type") or doc.get("category")
    )
    return DOC_DEFAULTS.get(doc_type, DOC_DEFAULTS["other"])["importance"]


def get_lead_time(doc) -> int:
    # Prefer stored lead time if valid
    try:
        lead = int(doc.get("renewal_lead_time_days"))
        if lead > 0:
            return lead
    except Exception:
        pass

    # Fallback to Service Default
    doc_type = normalize_doc_type(
        doc.get("doc_type") or doc.get("type") or doc.get("category")
    )
    return DOC_DEFAULTS.get(doc_type, DOC_DEFAULTS["other"])["lead"]


def brevo_send_email(to_email: str, subject: str, text_body: str) -> None:
    api_key = os.environ.get("BREVO_API_KEY")
    sender_email = os.environ.get("BREVO_SENDER_EMAIL")
    sender_name = os.getenv("BREVO_SENDER_NAME", "DocKeeper")

    if not api_key or not sender_email:
        raise ValueError("BREVO_API_KEY or BREVO_SENDER_EMAIL not set")

    payload = {
        "sender": {"email": sender_email, "name": sender_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": text_body,
    }

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


def format_in_days(days_until: int) -> str:
    if days_until < 0:
        d = abs(days_until)
        return f"expired {d} day{'s' if d != 1 else ''} ago"
    if days_until == 0:
        return "expires today"
    return f"in {days_until} day{'s' if days_until != 1 else ''}"


def process_digest(db, user_id, urgent_docs, risk_counts) -> None:
    # Fetch User Email
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = None

    if not user or not user.get("email"):
        # If user not found (or deleted), we skip
        return

    to_email = user["email"]

    # Check 7 day window
    state = db.notification_state.find_one({"user_id": user_id})
    last_sent = state.get("last_digest_at") if state else None

    if last_sent:
        # ensure last_sent is aware to match now(utc)
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)

        if (datetime.now(timezone.utc) - last_sent).days < 7:
            return

    # Construct Body
    critical = (risk_counts or {}).get("CRITICAL", 0)
    high = (risk_counts or {}).get("HIGH", 0)
    medium = (risk_counts or {}).get("MEDIUM", 0)
    low = (risk_counts or {}).get("LOW", 0)

    subject = f"DocKeeper Digest: {critical} critical, {high} high need attention"
    text_body = (
        "Hello,\n\n"
        f"You have {critical} CRITICAL and {high} HIGH risk documents that need attention:\n\n"
    )

    # Fetch user timezone to recalculate "today" for them
    from zoneinfo import ZoneInfo

    user_tz_str = user.get("timezone", "UTC")
    try:
        user_tz = ZoneInfo(user_tz_str)
    except Exception:
        user_tz = ZoneInfo("UTC")

    user_today = datetime.now(user_tz).date()

    for d in sorted(
        urgent_docs, key=lambda x: (x["risk"] != "CRITICAL", x["days_until"])
    ):

        utc_today = datetime.now(timezone.utc).date()
        delta_days = (user_today - utc_today).days

        adjusted_days = d["days_until"] - delta_days

        text_body += f" - {d['name']} ({d['risk']}): {format_in_days(adjusted_days)}\n"

    text_body += (
        "\nSummary:\n"
        f" - Medium risk: {medium}\n"
        f" - Low risk: {low}\n\n"
        "Log in to view all your documents and update expiry dates.\n"
    )

    # Mock or Real Send
    email_mode = os.environ.get("EMAIL_MODE", "mock").lower()

    if email_mode == "brevo":
        try:
            brevo_send_email(to_email, subject, text_body)
            print(f"Sent Brevo email to {to_email}", flush=True)
        except Exception as e:
            print(f"Failed to send Brevo email to {to_email}: {e}", flush=True)
            return  # Do not update state if failed
    else:
        # Mock Mode
        print(
            f"\n=== MOCK EMAIL DIGEST [To: {to_email} (User {user_id})] ===", flush=True
        )
        print(f"Subject: {subject}", flush=True)
        print(text_body, flush=True)
        print("================================================\n", flush=True)

    # Update State (only if success)
    db.notification_state.update_one(
        {"user_id": user_id},
        {"$set": {"last_digest_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


def run_once() -> None:

    now = datetime.now(timezone.utc)
    today = now.date()
    print(f"[{now.isoformat()}] {SERVICE_NAME} heartbeat", flush=True)

    try:
        db = get_db()

        urgent_by_user = {}
        risk_counts_by_user = {}

        processed = 0
        updated = 0
        skipped = 0

        # Only process non-archived documents
        for doc in db.documents.find({"archived": {"$ne": True}}):
            processed += 1

            expiry = parse_expiry_date(doc.get("expiry_date"))
            if expiry is None:
                skipped += 1
                continue

            days_until = (expiry - today).days
            importance = get_importance(doc)
            lead_time = get_lead_time(doc)

            risk = compute_risk_level(
                days_until_expiry=days_until,
                importance=importance,
                lead_time_days=lead_time,
            )

            # Aggregation for Digest
            uid = doc.get("user_id")
            if uid:
                risk_counts_by_user.setdefault(
                    uid, {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
                )
                bucket = (
                    risk if risk in ("CRITICAL", "HIGH", "MEDIUM", "LOW") else "UNKNOWN"
                )
                risk_counts_by_user[uid][bucket] += 1

                if risk in ("CRITICAL", "HIGH") or days_until < 0:
                    urgent_by_user.setdefault(uid, []).append(
                        {
                            "name": doc.get("name") or doc.get("label") or "Document",
                            "risk": risk,
                            "days_until": days_until,
                        }
                    )

            db.documents.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "last_checked_at": now,
                        "last_days_until": days_until,
                        "last_risk": risk,
                    }
                },
            )
            updated += 1

        # Process Digests
        for uid, docs in urgent_by_user.items():
            process_digest(db, uid, docs, risk_counts_by_user.get(uid))

        print(
            f"Processed={processed} Updated={updated} Skipped={skipped} "
            f"DigestsChecked={len(urgent_by_user)}",
            flush=True,
        )

    except Exception as e:
        print(f"Error connecting/processing DB: {e}", flush=True)


def main() -> None:
    print(
        f"{SERVICE_NAME} starting (interval={REMINDER_INTERVAL_SECONDS}s)", flush=True
    )
    try:
        while True:
            run_once()
            time.sleep(REMINDER_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        close_db_connection()
        print(f"{SERVICE_NAME} stopped", flush=True)


if __name__ == "__main__":  # pragma: no cover
    main()
