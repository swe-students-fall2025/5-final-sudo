# web-app/routers/health.py
from flask import Blueprint, jsonify

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify(status="ok")
