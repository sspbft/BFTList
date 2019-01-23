from flask import Blueprint, jsonify, current_app as app
from resolve.enums import Function, Module

routes = Blueprint("routes", __name__)


@routes.route("/", methods=["GET"])
def index():
    return jsonify({"status": "running", "service": "BFTList API"})


@routes.route("/view", methods=["GET"])
def view():
    view = app.resolver.execute(
        module=Module.VIEW_ESTABLISHMENT_MODULE,
        func=Function.GET_VIEW
    )
    return jsonify({"view": view})
