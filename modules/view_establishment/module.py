"""Contains code related to the View Establishment module Algorithm 1."""

from modules.algorithm_module import AlgorithmModule
import time


class ViewEstablishmentModule(AlgorithmModule):
    """Models the View Establishment module."""

    phs = []
    witnesses = []
    witnessesSet = {}
    echo = []

    def __init__(self, resolver, n=2):
        """Initializes the module."""
        self.resolver = resolver
        self.view = 0
        self.phs = [0] * n
        self.witness = [False] * n
        self.echo = [None] * n

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

    # Macros algorithm 1
    def echo_no_witn(self, node_k):
        """Method description.

        Checks if node k has reported(echo) a view and phase matching
        the current view and phase.
        """
        raise NotImplementedError

    def witnes_seen(self):
        """True if witnessSet (including current node) is greater than 4f."""
        raise NotImplementedError

    def next_phs(self):
        """Proceeds the phase from 0 to 1, or 1 to 0."""
        raise NotImplementedError
