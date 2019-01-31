"""Methods related to communication with BFTList nodes."""

import http.client
import json
from node import get_nodes
import time
from threading import Thread


def build_payload(op, val):
    """Builds a request object to be sent to all BFTList nodes."""
    return dict(operation=op, value=val)


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
            connection.request("POST", "/client/message", payload_json,
                               headers)
            sent = True
        except Exception:
            fails = fails + 1
            time.sleep(1)
            continue

    response = connection.getresponse()
    print(response.read().decode())


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
