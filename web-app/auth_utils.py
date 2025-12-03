from __future__ import annotations

# from typing import Optional
from bson import ObjectId
from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, user_id: str, email: str):
        self.id = user_id
        self.email = email

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

        return User(user_id=str(user_data["_id"]), email=user_data["email"])
