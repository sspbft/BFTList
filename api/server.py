"""Server that provides the BFTList API."""

# standard
from flask import Flask
from flask_cors import CORS
import os
import logging

# local
from api.routes import routes

# global
logger = logging.getLogger(__name__)


def create_app(resolver):
    """Creates the Flask app and injects a resolver."""
    app = Flask(
        "BFTList API",
        template_folder="api/templates",
        static_folder="api/static"
    )
    app.resolver = resolver
    app.register_blueprint(routes)
    CORS(app)
    return app


def start_server(resolver):
    """Starts the Flask server."""
    app = create_app(resolver)
    port = int(os.getenv("API_PORT", 4000))
    logger.info(f"API setup on port {port}")
    app.run(host="0.0.0.0", port=port)
