"""Contains code related to the Replication module."""

import time
from modules.algorithm_module import AlgorithmModule


class ReplicationModule(AlgorithmModule):
    """Models the Replication module."""

    def __init__(self, resolver):
        """Initializes the module."""
        self.resolver = resolver
        self.pending_reqs = []

    def get_pending_reqs(self):
        """Sample method."""
        return self.pending_reqs

    def run(self):
        """Called whenever the module is launched in a separate thread."""
        while True:
            # print(__name__ + ": running")
            time.sleep(1.5)
