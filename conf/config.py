"""Module handling config related actions."""
from communication.node import Node


def get_nodes(hosts_path="conf/hosts.txt"):
    """Parses nodes file to a list of Nodes."""
    with open(hosts_path) as f:
        lines = [x.strip().split(",") for x in f.readlines()]
        return list(map(lambda x: Node(id=x[0], hostname=x[1], ip=x[2],
                        port=x[3]), lines))
