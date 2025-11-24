# web-app/models.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class Document:
    """Data model for a document with expiry tracking.

    expiry_date is stored as a string (e.g. '2025-12-31').
    """

    id: int
    name: str
    category: str
    expiry_date: str
    importance: int = 3
    renewal_lead_time_days: int = 30
    notes: Optional[str] = None
