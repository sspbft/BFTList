"""Contains code related to the View Establishment module Algorithm 1."""

# standard
import logging
import os
import time
from copy import deepcopy
from itertools import compress

# local
from modules.algorithm_module import AlgorithmModule
from modules.view_establishment.predicates import PredicatesAndAction
from modules.enums import ViewEstablishmentEnums
from resolve.enums import MessageType
import conf.config as conf
from modules.constants import (VIEWS, PHASE, WITNESSES, CURRENT, NEXT)
import modules.byzantine as byz
from communication.zeromq.rate_limiter import throttle

logger = logging.getLogger(__name__)


class ViewEstablishmentModule(AlgorithmModule):
    """Models the View Establishment module."""

    def __init__(self, id, resolver, n, f):
        """Initializes the module."""
        self.resolver = resolver
        self.lock = resolver.view_est_lock
        self.phs = [0 for i in range(n)]
        self.witnesses = [False for i in range(n)]
        self.pred_and_action = PredicatesAndAction(self, id, self.resolver,
                                                   n, f)
        self.echo = [
            {VIEWS: {}, PHASE: 0, WITNESSES: {}}
            for i in range(n)
        ]

        self.number_of_nodes = n
        self.id = id
        self.number_of_byzantine = f
        self.witnesses_set = set()

        if os.getenv("INTEGRATION_TEST"):
            start_state = conf.get_start_state()
            if (start_state is not {} and str(self.id) in start_state and
               "VIEW_ESTABLISHMENT_MODULE" in start_state[str(self.id)]):
                data = start_state[str(self.id)]["VIEW_ESTABLISHMENT_MODULE"]
                if data is not None:
                    if "phs" in data:
                        self.phs = deepcopy(data["phs"])
                    if "views" in data:
                        self.pred_and_action.views = deepcopy(data["views"])
                    if "witnesses" in data:
                        self.witnesses = deepcopy(data["witnesses"])
                    if "echo" in data:
                        self.echo = deepcopy(data["echo"])
                    if "vChange" in data:
                        self.pred_and_action.vChange = deepcopy(
                                                        data["vChange"])

    def run(self, testing=False):
        """Called whenever the module is launched in a separate thread."""
        sec = os.getenv("INTEGRATION_TEST_SLEEP")
        time.sleep(int(sec) if sec is not None else 0)

        # block until system is ready
        while not testing and not self.resolver.system_running():
            time.sleep(0.1)

        while True:
            self.lock.acquire()
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
                        ViewEstablishmentEnums.PREDICATE,
                        self.phs[self.id],
                        case))
                ):
                    case += 1
                # Onces a predicates is fulfilled, perfom action if valid case
                if(self.pred_and_action.auto_max_case(self.phs[self.id]) >=
                        case):
                    # logger.info(f"Phase: {self.phs[self.id]} Case: {case}")
                    self.pred_and_action.automation(
                        ViewEstablishmentEnums.ACTION, self.phs[self.id], case)

            self.lock.release()
            # Stopping the while loop, used for testing purpose
            if testing:
                break

            # Send message to all other processors
            self.send_msg()
            throttle()

    # Macros
    def echo_no_witn(self, processor_k):
        """Method description.

        Checks if processor k has reported(echo) a view and phase matching
        the current view and phase.
        """
        return (self.pred_and_action.get_info(self.id) ==
                self.echo[processor_k].get(VIEWS) and
                self.phs[self.id] == self.echo[processor_k].get(PHASE))

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
        self.phs[self.id] = 0 if self.phs[self.id] == 1 else 1

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
            if self.echo_no_witn(processor_id):
                processor_set.add(processor_id)
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
    def get_current_view(self, processor_k):
        """Calls get_current_view of PredicatesAndAction."""
        return self.pred_and_action.get_current_view(processor_k)

    def allow_service(self):
        """Calls allow_service of PredicatesAndAction."""
        return self.pred_and_action.allow_service()

    def view_change(self):
        """Calls view_change of PredicatesAndAction."""
        return self.pred_and_action.view_change()

    # Methods to communicate with other processors
    def send_msg(self):
        """Method description.

        Calls the Resolver to send a message containing the phase, view and
        witnesses of processor i and what processor wants to echo about
        processor j to processor_j
        """
        # stay silent if node configured to be unresponsive
        if byz.is_byzantine() and byz.get_byz_behavior() == byz.UNRESPONSIVE:
            logger.info(f"Node is acting byzantine: {byz.UNRESPONSIVE}")
            return

        nodes = conf.get_nodes()
        for node_j, _ in nodes.items():
            # update own echo instead of sending message
            if node_j == self.id:
                self.echo[self.id] = {
                    VIEWS: self.pred_and_action.get_info(self.id),
                    PHASE: self.phs[self.id],
                    WITNESSES: self.witnesses[self.id]
                }
            else:
                # node_i's own data
                own_data = [deepcopy(self.phs[self.id]),
                            deepcopy(self.witnesses[self.id]),
                            deepcopy(self.pred_and_action.get_info(self.id))
                            ]

                # what node_i thinks about node_j
                about_data = [deepcopy(self.phs[node_j]),
                              deepcopy(self.witnesses[node_j]),
                              deepcopy(self.pred_and_action.get_info(node_j))
                              ]

                # Overwriting own_data to send different views to different
                # nodes, to trick them
                # if acting Byzantine with different_views - behaviour
                if byz.is_byzantine():
                    if byz.get_byz_behavior() == byz.DIFFERENT_VIEWS:
                        logger.info(
                            f"Node is acting byzantine: {byz.DIFFERENT_VIEWS}")
                        if (node_j % 2 == 0):
                            own_data = [0,
                                        True,
                                        {CURRENT: 1, NEXT: 1}
                                        ]
                        else:
                            own_data = [0,
                                        True,
                                        {CURRENT: 2, NEXT: 2}
                                        ]
                    elif byz.get_byz_behavior() == byz.FORCING_RESET:
                        logger.info(
                            f"Node is acting byzantine: {byz.FORCING_RESET}")
                        own_data = [0,
                                    True,
                                    self.pred_and_action.RST_PAIR
                                    ]

                msg = {"type": MessageType.VIEW_ESTABLISHMENT_MESSAGE,
                       "sender": self.id,
                       "data": {
                                "own_data": deepcopy(own_data),
                                "about_data": deepcopy(about_data)
                            }
                       }
                self.resolver.send_to_node(node_j, msg)

    def receive_msg(self, msg):
        """Method description.

        Resolver calls this function when a message to the View Establishment
        module from another processor has been delievered.
        Validates the message and updates phase, witnesses, echo and views for
        the sending processor.
        """
        # id of sender
        j = msg["sender"]
        # j's own data
        j_own_data = deepcopy(msg["data"]["own_data"])
        # what j thinks about me
        j_about_data = deepcopy(msg["data"]["about_data"])

        if(self.pred_and_action.valid(j_own_data)):
            self.echo[j] = {
                PHASE: deepcopy(j_about_data[0]),
                WITNESSES: deepcopy(j_about_data[1]),
                VIEWS: deepcopy(j_about_data[2])
            }

            self.phs[j] = deepcopy(j_own_data[0])
            self.witnesses[j] = deepcopy(j_own_data[1])
            self.pred_and_action.set_info(deepcopy(j_own_data[2]), j)
        else:
            logger.info(f"Not a valid message from " +
                        f"node {j}: {j_own_data}")

    # Function to extract data
    def get_data(self):
        """Returns current values on local variables."""
        return {
            "id": self.id,
            "phs": self.phs,
            "views": self.pred_and_action.views,
            "vChange": self.pred_and_action.vChange,
            "witnesses": self.witnesses,
            "witnesses_set": self.witnesses_set,
            "echo": self.echo,
            "primary": self.get_current_view(self.id)
        }
