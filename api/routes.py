"""Contains all API routes for the external REST API."""

# standard
import os
import json
import jsonpickle
from flask import (Blueprint, jsonify, request, abort,
                   render_template, current_app as app)
from flask_cors import cross_origin
import requests
import logging

# local
import conf.config as conf
import modules.byzantine as byz
from modules.replication.models.request import Request
from modules.replication.models.client_request import ClientRequest
from modules.replication.models.operation import Operation

# globals
routes = Blueprint("routes", __name__)
logger = logging.getLogger(__name__)


class CustomEncoder(json.JSONEncoder):
    """Encoder with support for sets."""

    def default(self, obj):
        """Converts set to list, all other datatypes are treated as usual."""
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, (Request, ClientRequest, Operation)):
            return obj.to_dct()
        return json.JSONEncoder.default(self, obj)


@routes.route("/", methods=["GET"])
def index():
    """Return the status of the current API service."""
    _id = str(os.getenv("ID", 0))
    return jsonify({
        "status": app.resolver.system_status.name,
        "service": "BFTList",
        "id": _id
    })


@routes.route("/inject-client-req", methods=["POST"])
def handle_client_message():
    """Route for clients to send messages to a node."""
    data = request.get_json()
    if not ("operation" in data and "client_id" in data and
            "timestamp" in data and "type" in data["operation"] and
            "args" in data["operation"]):
        return abort(400)

    try:
        op = Operation(data["operation"]["type"], data["operation"]["args"])
        req = ClientRequest(data["client_id"], data["timestamp"], op)
        pend_reqs = app.resolver.inject_client_req(req)
        logger.info(f"Injected req {req} to pend_reqs")
        return jsonify({"pend_reqs": jsonpickle.encode(pend_reqs)})
    except Exception as e:
        logger.error(f"Error when injecting client request through API: {e}")
        return abort(500)


@routes.route("/set-byz-behavior", methods=["POST"])
def set_byz_behavior():
    """Route for setting Byzantine behavior for this node at runtime."""
    data = request.get_json()
    behavior = data["behavior"]
    if not byz.is_valid_byz_behavior(behavior):
        return abort(400)

    byz.set_byz_behavior(behavior)
    return jsonify({"behavior": byz.get_byz_behavior()})


@routes.route("/byz-behaviors", methods=["GET"])
def get_byz_behaviors():
    """Returns the valid Byzantine behaviors."""
    return jsonify(byz.BYZ_BEHAVIORS)


@routes.route("/data", methods=["GET"])
@cross_origin()
def get_modules_data():
    """Returns current values of variables in the modules."""
    test_name = os.getenv("INTEGRATION_TEST")
    test_data = {"test_name": test_name} if test_name else None

    data = {"VIEW_ESTABLISHMENT_MODULE":
            app.resolver.get_view_establishment_data(),
            "REPLICATION_MODULE":
            app.resolver.get_replication_data(),
            "PRIMARY_MONITORING_MODULE":
            app.resolver.get_primary_monitoring_data(),
            "node_id": int(os.getenv("ID")),
            "test_data": test_data,
            "byzantine": byz.is_byzantine(),
            "byzantine_behavior": byz.get_byz_behavior()
            }
    return json.dumps(data, cls=CustomEncoder)


def fetch_data_for_all_nodes():
    """Fetches data from all nodes through their /data endpoint."""
    try:
        data = []
        for _, node in conf.get_nodes().items():
            r = requests.get(f"http://{node.ip}:{4000+node.id}/data")
            data.append({"node": node.to_dct(), "data": r.json()})
        return data
    except Exception as e:
        logger.error(f"Error when fetching data for other nodes: {e}")
        return None


def render_global_view(view="view-est"):
    """Renders the global view for a specified module."""
    nodes_data = fetch_data_for_all_nodes()
    if nodes_data is None:
        return jsonify({"STATUS": "SYSTEM_BOOT"})

    test_name = os.getenv("INTEGRATION_TEST")
    test_data = {"test_name": test_name} if test_name is not None else {}

    return render_template("view/main.html", data={
        "view": view,
        "nodes_data": nodes_data,
        "test_data": test_data,
        "byz_behaviors": [byz.NONE] + byz.BYZ_BEHAVIORS
    })


@routes.route("/view/view-est", methods=["GET"])
def render_view_est_view():
    """Renders the global view for the View Establishment module.

    This view only displays data related to the view est module and should
    only be used when running integration test for that module.
    """
    return render_global_view("view-est")


@routes.route("/view/rep", methods=["GET"])
def render_rep_view():
    """Renders the global view for the Replication module.

    This view only displays data related to the rep module and should
    only be used when running integration test for that module.
    """
    return render_global_view("rep")


@routes.route("/view/prim-mon", methods=["GET"])
def render_prim_mon_view():
    """Renders the global view for the Primary Monitoring module.

    This view only displays data related to the prim monitoring module and
    should only be used when running integration test for that module.
    """
    return render_global_view("prim-mon")
