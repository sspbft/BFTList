"""Contains code related to the View Establishment module."""

from modules.algorithm_module import AlgorithmModule
import time


class ViewEstablishmentModule(AlgorithmModule):
    """Models the View Establishment module."""

    def __init__(self, resolver):
        """Initializes the module."""
        self.resolver = resolver
        self.view = 0

    def run(self):
        """Called whenever the module is launched in a separate thread."""
        while True:
            # print(__name__ + ": running")
            time.sleep(3)

    def get_view(self):
        """Sample method."""
        print("ViewEstablishmentModule: call to get_view")
        ret = self.view
        self.view = ret + 1
        return ret
