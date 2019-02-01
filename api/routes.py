"""Contains all API routes for the external REST API."""

# import current_app as app and access resolver through app.resolver
from flask import Blueprint, jsonify
import os

routes = Blueprint("routes", __name__)
lst = []


@routes.route("/", methods=["GET"])
def index():
    """Return the status of the current API service."""
    _id = str(os.getenv("ID", 0))
    return jsonify({"status": "running", "service": "BFTList API", "id": _id})


@routes.route("/client/message", methods=["POST"])
def handle_client_message():
    """Route for clients to send messages to a node."""
    # TODO implement
    return jsonify({"error": "NOT_IMPLEMENTED"})
