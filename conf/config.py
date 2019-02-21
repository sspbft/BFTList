"""Module handling config related actions."""

# standard
import os
import logging
import jsonpickle

# local
from communication.node import Node

# globals
logger = logging.getLogger(__name__)


def get_nodes(hosts_path="conf/hosts.txt"):
    """Parses nodes file to a dict of nodes such that dct[id] = node.

    Can be overridden by specifying the environment variable HOSTS_PATH, which
    corresponds to the absolute path to the desired hosts file.
    """
    if os.getenv("HOSTS_PATH"):
        hosts_path = os.getenv("HOSTS_PATH")
    try:
        with open(hosts_path) as f:
            lines = [x.strip().split(",") for x in f.readlines()]
            nodes = {}
            for l in lines:
                nodes[int(l[0])] = Node(id=l[0], hostname=l[1], ip=l[2],
                                        port=l[3])
            return nodes
    except FileNotFoundError as e:
        logger.error(e)


def get_other_nodes():
    """Helper that returns all other nodes in the system."""
    all_nodes = get_nodes()
    own_id = int(os.getenv("ID"))
    all_nodes.pop(own_id)
    return all_nodes


def get_start_state():
    """Gets start state for this node."""
    path = os.path.abspath("./conf/start_state.json")
    try:
        with open(path) as f:
            decoded = f.read().replace('\n', '')
            data = jsonpickle.decode(decoded)
            return data
    except FileNotFoundError:
        return {}
