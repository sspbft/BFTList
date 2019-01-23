from flask import Flask, jsonify
from resolver.enums import Function, Module

app = Flask("BFTList API")

@app.route("/")
def index():
    return jsonify({ "status": "running", "service": "BFTList API" })

def start_server(resolver):
    # TODO use resolver and bind to instance of app in its own thread
    # https://stackoverflow.com/questions/32298960/werkzeug-and-class-state-with-flask-how-are-class-member-variables-resetting-wh
    app.run()
    