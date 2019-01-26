"""Server that provides the BFTList API."""

from flask import Flask
from api.routes import routes
import os


def create_app(resolver):
    """Creates the Flask app and injects a resolver."""
    app = Flask("BFTList API")
    app.resolver = resolver
    app.register_blueprint(routes)
    return app


def start_server(resolver):
    """Foo bar baz."""
    app = create_app(resolver)
    port = int(os.getenv("API_PORT", 4000))
    app.run(port=port)
