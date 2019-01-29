"""Contains code related to the View Establishment module Algorithm 1."""

from modules.algorithm_module import AlgorithmModule
from modules.view_establishment.predicates import PredicatesAndAction
import time


class ViewEstablishmentModule(AlgorithmModule):
    """Models the View Establishment module."""

    phs = []
    witnesses = []
    witnessesSet = {}
    echo = []
    pred_and_action = None

    def __init__(self, resolver, n=2):
        """Initializes the module."""
        self.resolver = resolver
        self.view = 0
        self.phs = [0] * n
        self.witness = [False] * n
        self.echo = [None] * n
        self.pred_and_action = PredicatesAndAction(self, self.resolver, n)

    def run(self):
        """Called whenever the module is launched in a separate thread."""
        while True:
            # print(__name__ + ": running")
            time.sleep(3)

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

    # Interface functions

    def get_phs(node_k):
        """Returns the phase of node k according to current node."""
        raise NotImplementedError

    def init_module(self):
        """Use to reset the module."""
        raise NotImplementedError

    # TODO Change this to direct communication with Algorithm 2
    # , remove default values
    # Methods to communicate with Algorithm 2 (still View Establishment Module)
    def get_view(self, node_k=0):
        """Calls get_view of PredicatesAndAction."""
        return self.pred_and_action.get_view(node_k)

    def allow_service(self):
        """Calls allow_service of PredicatesAndAction."""
        return self.pred_and_action.allow_service()
