"""Methods related to communication with BFTList nodes."""

# standard
import http.client
import json
import time
from threading import Thread

# local
from node import get_nodes


def build_payload(op, args):
    """Builds a request object to be sent to all BFTList nodes."""
    return {
        "client_id": 0,
        "timestamp": int(time.time()),
        "operation": {
            "type": op,
            "args": args
        }
    }


def send_to_node(node, payload):
    """
    Sends the given payload as a POST request to a Node.

    Tries to send the request up to 5 times with 1 second interval, will
    quit if 5 failed attempts is reached.
    """
    sent = False
    fails = 0
    connection = http.client.HTTPConnection(node.ip, node.api_port)
    headers = {"Content-type": "application/json"}
    payload_json = json.dumps(payload)
    while not sent and fails < 5:
        try:
            connection.request("POST", "/inject-client-req", payload_json,
                               headers)
            sent = True
        except Exception:
            fails = fails + 1
            time.sleep(1)
            continue


def broadcast(payload):
    """Broadcast the request to all running BFTList nodes."""
    nodes = get_nodes()
    threads = []
    for _, node in nodes.items():
        t = Thread(target=send_to_node, args=(node, payload))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    print(f"Sending payload {payload} to all nodes")
    return
