"""Contains all API routes for the external REST API."""

# import current_app as app and access resolver through app.resolver
from flask import Blueprint, jsonify, current_app as app
import os

routes = Blueprint("routes", __name__)


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


@routes.route("/data", methods=["GET"])
def get_modules_data():
    """Returns current values of variables in the modules."""
    data = {"VIEW_ESTABLISHMENT_MODULE":
            app.resolver.get_view_establishment_data(),
            "REPLICATION_MODULE":
            app.resolver.get_replication_data(),
            "PRIMARY_MONITORING_MODULE":
            app.resolver.get_primary_monitoring_data()
            }
    return jsonify(data)
