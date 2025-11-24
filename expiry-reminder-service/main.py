# expiry-reminder-service/main.py
import os
import time
from pymongo import MongoClient
from pymongo.database import Database

# Configuration
SERVICE_NAME = "DocKeeper Expiry Reminder Service"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "dockeeper")
REMINDER_INTERVAL_SECONDS = int(os.getenv("REMINDER_INTERVAL_SECONDS", "60"))

# Database connection
_client = None


def get_mongo_client() -> MongoClient:
    """Get or create MongoDB client."""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client


def get_db() -> Database:
    """Get MongoDB database handle."""
    client = get_mongo_client()
    return client[MONGO_DB_NAME]


def close_db_connection():
    """Close MongoDB connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def run_once() -> None:
    """Single pass of the reminder service.

    Reads documents from MongoDB, computes risk levels,
    and logs summary information.
    """
    from datetime import datetime, date
    from logic import compute_risk_level

    now = datetime.utcnow().isoformat()
    print(f"[{now}] {SERVICE_NAME} heartbeat", flush=True)

    try:
        db = get_db()
        documents = list(db.documents.find())

        print(f"Found {len(documents)} document(s) in database", flush=True)

        # Process a few documents to demonstrate risk calculation
        for doc in documents[:3]:  # Just first 3 for demo
            try:
                # Parse expiry date and calculate days until expiry
                expiry_str = doc.get("expiry_date", "")
                if expiry_str:
                    expiry_date = datetime.fromisoformat(expiry_str).date()
                    days_until = (expiry_date - date.today()).days
                    importance = doc.get("importance", 3)
                    risk = compute_risk_level(days_until, importance)

                    print(
                        f"  - {doc.get('name', 'Unknown')}: "
                        f"{days_until} days until expiry, "
                        f"risk level: {risk}",
                        flush=True,
                    )
            except Exception as e:
                print(f"  - Error processing document: {e}", flush=True)

    except Exception as e:
        print(f"Error connecting to database: {e}", flush=True)


def main() -> None:
    """Main loop for the reminder service."""
    interval = REMINDER_INTERVAL_SECONDS
    while True:
        run_once()
        time.sleep(interval)


if __name__ == "__main__":
    main()
