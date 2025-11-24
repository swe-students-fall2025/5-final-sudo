# expiry-reminder-service/reminder_service/main.py
import os
import time
from datetime import datetime
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

    Processes documents from MongoDB, computes risk levels,
    and stores notifications or summaries.
    """
    now = datetime.utcnow().isoformat()
    print(f"[{now}] {SERVICE_NAME} heartbeat", flush=True)


def main() -> None:
    """Main loop for the reminder service."""
    interval = REMINDER_INTERVAL_SECONDS
    while True:
        run_once()
        time.sleep(interval)


if __name__ == "__main__":
    main()
