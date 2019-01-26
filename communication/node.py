"""This module contains code modelling nodes in the distributed system."""


class Node:
    """Class representing a node."""

    def __init__(self, id, hostname, ip, port):
        """Initializes a node."""
        self.id = int(id)
        self.hostname = hostname
        self.ip = ip
        self.port = int(port)
