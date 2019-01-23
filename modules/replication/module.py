import time
from modules.algorithm_module import AlgorithmModule


class ReplicationModule(AlgorithmModule):
    def __init__(self, resolver):
        self.resolver = resolver
        self.pending_reqs = []

    def get_pending_reqs(self):
        return self.pending_reqs

    def run(self):
        while True:
            # print(__name__ + ": running")
            time.sleep(1.5)
