"""Contains code related to the View Establishment module Algorithm 1."""

from modules.algorithm_module import AlgorithmModule
from modules.view_establishment.predicates import PredicatesAndAction
from modules.enums import ViewEstablishmentEnums
from itertools import compress


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
        # while True:
        if(self.pred_and_action.need_reset()):
            self.pred_and_action.reset_all()
        self.witnesses[self.id] = self.noticed_recent_value()
        self.witnesses_set = self.witnesses_set.union(self.get_witnesses())
        if (self.witnes_seen()):
            case = 0
            # Find the current case by testing the predicates and
            # moving to next case if not fulfilled
            while (self.pred_and_action.auto_max_case(
                self.phs[self.id]) >= case and not
                (self.pred_and_action.automation(
                    ViewEstablishmentEnums.PREDICATE, self.phs[self.id], case))
            ):
                case += 1
            # Onces a predicates is fulfilled, perfom action if valid case
            if(self.pred_and_action.auto_max_case(self.phs[self.id]) >=
                    case):
                ret = self.pred_and_action.automation(
                    ViewEstablishmentEnums.ACTION, self.phs[self.id], case)
                # Move to next phase if the return value is not a
                # no_action or reset
                if (ret != ViewEstablishmentEnums.NO_ACTION and
                        ret != ViewEstablishmentEnums.RESET):
                    self.next_phs()

        # Send message to all other processors
        for processor_id in range(self.number_of_nodes):
            self.send_msg(processor_id)

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

    # Help methods for the while true loop

    def noticed_recent_value(self):
        """Method description.

        Returns true if 4f+1 processors have noticed the recent value of
        processors i view and phase
        """
        processor_set = set()
        for processor_id in range(self.number_of_nodes):
            (processor_set.add(processor_id) if
                self.echo_no_witn(processor_id)
                else None)
        return len(processor_set) >= (4 * self.number_of_byzantine + 1)

    def get_witnesses(self):
        """Method description.

        Returns the set of processors that processor i knows that they have
        been witnessed.
        """
        processor_set = set(compress(range(len(self.witnesses)),
                            self.witnesses))
        return processor_set

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
