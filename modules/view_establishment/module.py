"""Contains code related to the View Establishment module Algorithm 1."""

from modules.algorithm_module import AlgorithmModule
from modules.view_establishment.predicates import PredicatesAndAction
import time


class ViewEstablishmentModule(AlgorithmModule):
    """Models the View Establishment module."""

    VIEWS = "views"
    PHASE = "phase"
    WITNESSES = "witnesses"

    phs = []
    witnesses = []
    witnesses_set = set()
    echo = []
    pred_and_action = None
    resolver = None
    number_of_nodes = 0
    number_of_byzantine = 0
    id = 0

    def __init__(self, resolver, id=0, n=2, byz=0):
        """Initializes the module."""
        self.resolver = resolver
        self.phs = [0 for i in range(n)]
        self.witnesses = [False for i in range(n)]
        self.echo = [
            {self.VIEWS: None, self.PHASE: None, self.WITNESSES: None}
            for i in range(n)
        ]
        self.pred_and_action = PredicatesAndAction(self, self.resolver, n)
        self.number_of_nodes = n
        self.id = id
        self.number_of_byzantine = byz

    def run(self):
        """Called whenever the module is launched in a separate thread."""
        while True:
            time.sleep(3)

    # Macros
    def echo_no_witn(self, processor_k):
        """Method description.

        Checks if processor k has reported(echo) a view and phase matching
        the current view and phase.
        """
        return (self.get_view(self.id) ==
                self.echo[processor_k].get(self.VIEWS) and
                self.phs[self.id] == self.echo[processor_k].get(self.PHASE))

    def witnes_seen(self):
        """Method description.

        True if witnessSet (including current node) is greater than 4f and
        processor i has been witnessed.
        """
        if(self.witnesses[self.id]):
            processor_set = set()
            for processor_id in self.witnesses_set:
                if(self.echo[self.id] == self.echo[processor_id]):
                    processor_set.add(processor_id)
            processor_set.union({self.id})
            return (len(processor_set) >= (4 * self.number_of_byzantine + 1))
        return False

    def next_phs(self):
        """Proceeds the phase from 0 to 1, or 1 to 0."""
        self.phs[self.id] ^= 1

    # Interface functions
    def get_phs(self, processor_k):
        """Returns the phase of node k according to current node."""
        return self.phs[processor_k]

    def init_module(self):
        """Use to reset the module."""
        self.phs = [0 for i in range(self.number_of_nodes)]
        self.witnesses = [False for i in range(self.number_of_nodes)]
        self.witnesses_set = set()

    # Methods to communicate with Algorithm 2 (View Establishment Module)
    def get_view(self, processor_k):
        """Calls get_view of PredicatesAndAction."""
        return self.pred_and_action.get_view(processor_k)

    def allow_service(self):
        """Calls allow_service of PredicatesAndAction."""
        return self.pred_and_action.allow_service()

    # Methods to communicate with other processors
    def send_msg(self, processor_j):
        """Method description.

        Calls the Resolver to send a message containing the phase, view and
        witnesses of processor i and what processor wants to echo about
        processor j to processor_j
        """
        raise NotImplementedError

    def receive_msg(self, msg):
        """Method description.

        Resolver calls this function when a message to the View Establishment
        module from another processor has been delievered.
        Valids the message and updates phase, witnesses, echo and views for the
        sending processor.
        """
        raise NotImplementedError
