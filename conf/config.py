"""Module handling config related actions."""
from communication.node import Node


def get_nodes(hosts_path="conf/hosts.txt"):
    """Parses nodes file to a dict of nodes such that dct[id] = node."""
    with open(hosts_path) as f:
        lines = [x.strip().split(",") for x in f.readlines()]
        nodes = {}
        for l in lines:
            nodes[int(l[0])] = Node(id=l[0], hostname=l[1], ip=l[2], port=l[3])
        return nodes
