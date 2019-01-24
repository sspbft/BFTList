"""Contains all API routes for the external REST API."""

from flask import Blueprint, jsonify, current_app as app
from resolve.enums import Function, Module

routes = Blueprint("routes", __name__)


@routes.route("/", methods=["GET"])
def index():
    """Return the status of the current API service."""
    return jsonify({"status": "running", "service": "BFTList API"})


@routes.route("/view", methods=["GET"])
def view():
    """Sample route that fetches data from a module and returns it."""
    view = app.resolver.execute(
        module=Module.VIEW_ESTABLISHMENT_MODULE,
        func=Function.GET_VIEW
    )
    return jsonify({"view": view})
