# web-app/main.py
import os

from flask import Flask, render_template

from routers.health import bp as health_bp
from routers.documents import bp as documents_bp

APP_NAME = "DocKeeper - Expiry Tracker"

# MongoDB configuration for future use
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "dockeeper")


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(documents_bp)

    @app.route("/")
    def index():
        """Home page dashboard."""
        return render_template("index.html", title="DocKeeper")

    return app


# For tests and local running
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
