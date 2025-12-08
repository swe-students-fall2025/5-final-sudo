# web-app/main.py
import os

from flask import Flask, render_template
from pymongo import MongoClient
from flask_login import LoginManager

from routers.health import bp as health_bp
from routers.documents import bp as documents_bp
from routers.auth import bp as auth_bp

APP_NAME = "DocKeeper - Expiry Tracker"

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "dockeeper")

# Global MongoDB client
_mongo_client = None


def get_mongo_client():
    """Get or create MongoDB client."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI)
    return _mongo_client


def get_db():
    """Get MongoDB database."""
    client = get_mongo_client()
    return client[MONGO_DB_NAME]


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")

    # Sessions (required for login cookies)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    if not app.config["SECRET_KEY"]:
        raise ValueError("No SECRET_KEY set for Flask application")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # init Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)

    from auth_utils import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(auth_bp)

    @app.route("/")
    def index():
        """Home page dashboard."""
        return render_template("index.html", title="DocKeeper")

    return app


# For tests and local running
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
