"""Server that provides the BFTList API."""

from flask import Flask, jsonify
from resolve.enums import Function, Module
from api.routes import routes


def create_app(resolver):
    app = Flask("BFTList API")
    app.resolver = resolver
    app.register_blueprint(routes)
    return app


def start_server(resolver):
    app = create_app(resolver)
    app.run()
