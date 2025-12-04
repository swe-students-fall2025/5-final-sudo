# expiry-reminder-service/main.py
import os
import time
from datetime import datetime, date
from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database

from logic import compute_risk_level

SERVICE_NAME = "DocKeeper Expiry Reminder Service"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "dockeeper")
REMINDER_INTERVAL_SECONDS = int(os.getenv("REMINDER_INTERVAL_SECONDS", "60"))

_client: Optional[MongoClient] = None

DOC_IMPORTANCE_DEFAULTS = {
    "passport": 5,
    "visa": 5,
    "driver_license": 4,
    "car_registration": 4,
    "insurance": 4,
    "lease": 5,
    "permit": 3,
    "subscription": 2,
    "warranty": 2,
    "other": 3,
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
    return v if v in DOC_IMPORTANCE_DEFAULTS else "other"


def get_importance(doc) -> int:
    # Prefer stored importance if valid; otherwise infer from doc_type.
    try:
        imp = int(doc.get("importance"))
        if 1 <= imp <= 5:
            return imp
    except Exception:
        pass

    doc_type = normalize_doc_type(
        doc.get("doc_type") or doc.get("type") or doc.get("category")
    )
    return DOC_IMPORTANCE_DEFAULTS.get(doc_type, 3)


def run_once() -> None:
    now = datetime.utcnow()
    today = now.date()
    print(f"[{now.isoformat()}] {SERVICE_NAME} heartbeat", flush=True)

    try:
        db = get_db()

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
            lead_time = max(1, int(doc.get("renewal_lead_time_days") or 30))

            risk = compute_risk_level(
                days_until_expiry=days_until,
                importance=importance,
                lead_time_days=lead_time,
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

        print(
            f"Processed={processed} Updated={updated} Skipped(no/invalid expiry)={skipped}",
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


if __name__ == "__main__":
    main()
