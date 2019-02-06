"""Contains all API routes for the external REST API."""

# import current_app as app and access resolver through app.resolver
import os
import json

from flask import Blueprint, jsonify, render_template, current_app as app
from flask_cors import cross_origin
import requests

import conf.config as conf

routes = Blueprint("routes", __name__)


class CustomEncoder(json.JSONEncoder):
    """Encoder with support for sets."""

    def default(self, obj):
        """Converts set to list, all other datatypes are treated as usual."""
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, "Node"):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)


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
@cross_origin()
def get_modules_data():
    """Returns current values of variables in the modules."""
    data = {"VIEW_ESTABLISHMENT_MODULE":
            app.resolver.get_view_establishment_data(),
            "REPLICATION_MODULE":
            app.resolver.get_replication_data(),
            "PRIMARY_MONITORING_MODULE":
            app.resolver.get_primary_monitoring_data(),
            "node_id": int(os.getenv("ID"))
            }
    return json.dumps(data, cls=CustomEncoder)


def fetch_data_for_all_nodes():
    """Fetches data from all nodes through their /data endpoint."""
    # data = [{ node: node, data: json }]
    data = []
    for _, node in conf.get_nodes().items():
        r = requests.get(f"http://{node.ip}:400{node.id}/data")
        data.append({"node": node.to_dct(), "data": r.json()})
    return data


@routes.route("/view", methods=["GET"])
def render_view():
    """Renders the global view page."""
    data = fetch_data_for_all_nodes()
    # for _, node in conf.get_nodes().items():
    #     data.append(node)
    return render_template("view.html", data=data)
