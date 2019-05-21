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
from resolve.enums import Module, Function
import conf.config as conf
from modules.constants import (VIEWS, PHASE, WITNESSES, CURRENT, NEXT, VCHANGE)
import modules.byzantine as byz
from communication.zeromq.rate_limiter import throttle

# metrics
from metrics.messages import run_method_time
from metrics.convegence_latency import suspect_prim

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
            {VIEWS: {}, PHASE: 0, WITNESSES: {}, VCHANGE: None}
            for i in range(n)
        ]

        self.number_of_nodes = n
        self.id = id
        self.number_of_byzantine = f
        self.witnesses_set = set()
        self.correct_ids = []
        self.last_correct_ids = []

        if os.getenv("INTEGRATION_TEST") or os.getenv("INJECT_START_STATE"):
            start_state = conf.get_start_state()
            if (start_state is not {} and str(self.id) in start_state and
               "VIEW_ESTABLISHMENT_MODULE" in start_state[str(self.id)]):
                data = start_state[str(self.id)]["VIEW_ESTABLISHMENT_MODULE"]
                if data is not None:
                    logger.warning("Injecting start state")
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

        ts = time.time()
        while True:
            self.correct_ids = self.resolver.execute(
                Module.EVENT_DRIVEN_FD_MODULE,
                Function.GET_CORRECT_PROCESSORS_FOR_TIMESTAMP,
                ts)
            if self.correct_ids != []:
                self.lock.acquire()
                start_time = time.time()
                self.last_correct_ids = deepcopy(self.correct_ids)

                if(self.pred_and_action.need_reset()):
                    self.pred_and_action.reset_all()
                self.witnesses[self.id] = self.noticed_recent_value()
                self.witnesses_set = self.witnesses_set.union(
                    self.get_witnesses())
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
                    # Onces a predicate is fulfilled, perfom action if valid
                    # case
                    if(self.pred_and_action.auto_max_case(self.phs[self.id]) >=
                            case):
                        self.pred_and_action.automation(
                            ViewEstablishmentEnums.ACTION,
                            self.phs[self.id],
                            case
                        )
                    ts = time.time()
                # Emit run time metric
                # ts = time.time()
                run_time = time.time() - start_time
                run_method_time.labels(
                    self.id,
                    Module.VIEW_ESTABLISHMENT_MODULE).set(
                    run_time
                )
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
        predicate_info = self.pred_and_action.get_info(self.id)
        return (predicate_info[0] ==
                self.echo[processor_k].get(VIEWS) and
                self.phs[self.id] == self.echo[processor_k].get(PHASE) and
                predicate_info[1] == self.echo[processor_k].get(VCHANGE))

    def witnes_seen(self):
        """Method description.

        True if witnessSet (including current node) is greater than 4f and
        processor i has been witnessed.
        """
        if(self.witnesses[self.id]):
            processor_set = set()
            for processor_id in self.witnesses_set:
                if not self.is_correct(processor_id):
                    continue
                if(self.echo[self.id] == self.echo[processor_id]):
                    processor_set.add(processor_id)
            processor_set.union({self.id})
            # return (len(processor_set) >= (4 * self.number_of_byzantine + 1))
            return (len(processor_set) >= (self.number_of_nodes -
                                           self.number_of_byzantine))

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
            if not self.is_correct(processor_id):
                continue
            if self.echo_no_witn(processor_id):
                processor_set.add(processor_id)
        # return len(processor_set) >= (4 * self.number_of_byzantine + 1)
        return len(processor_set) >= (self.number_of_nodes -
                                      self.number_of_byzantine)

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
        suspect_prim(self.get_current_view(self.id))
        self.resolver.on_experiment_start()
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
            return

        nodes = conf.get_nodes()
        for node_j, _ in nodes.items():
            # update own echo instead of sending message
            if node_j == self.id:
                predicate_info = self.pred_and_action.get_info(self.id)
                self.echo[self.id] = {
                    VIEWS: predicate_info[0],
                    PHASE: self.phs[self.id],
                    WITNESSES: self.witnesses[self.id],
                    VCHANGE: predicate_info[1]
                }
            else:
                # node_i's own data
                pred_and_action_own_data = self.pred_and_action.get_info(
                                                self.id)
                own_data = [deepcopy(self.phs[self.id]),
                            deepcopy(self.witnesses[self.id]),
                            deepcopy(pred_and_action_own_data[0]),
                            deepcopy(pred_and_action_own_data[1])
                            ]
                pred_and_action_about_data = self.pred_and_action.get_info(
                                                node_j)
                # what node_i thinks about node_j
                about_data = [deepcopy(self.phs[node_j]),
                              deepcopy(self.witnesses[node_j]),
                              deepcopy(pred_and_action_about_data[0]),
                              deepcopy(pred_and_action_about_data[1])
                              ]

                # Overwriting own_data to send different views to different
                # nodes, to trick them
                # if acting Byzantine with different_views - behaviour
                if byz.is_byzantine():
                    if byz.get_byz_behavior() == byz.DIFFERENT_VIEWS:
                        if (node_j % 2 == 0):
                            own_data = [0,
                                        True,
                                        {CURRENT: 1, NEXT: 1},
                                        False
                                        ]
                        else:
                            own_data = [0,
                                        True,
                                        {CURRENT: 2, NEXT: 2},
                                        False
                                        ]
                    elif byz.get_byz_behavior() == byz.FORCING_RESET:
                        own_data = [0,
                                    True,
                                    self.pred_and_action.RST_PAIR,
                                    False
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
                VIEWS: deepcopy(j_about_data[2]),
                VCHANGE: deepcopy(j_about_data[3])
            }

            self.phs[j] = deepcopy(j_own_data[0])
            self.witnesses[j] = deepcopy(j_own_data[1])
            self.pred_and_action.set_info(deepcopy(j_own_data[2]),
                                          deepcopy(j_own_data[3]),
                                          j)
        else:
            logger.info(f"Not a valid message from " +
                        f"node {j}: {j_own_data}")

    def is_correct(self, id):
        """TODO write me."""
        return id in self.last_correct_ids

    def get_correct_ids(self):
        """TODO write me."""
        return self.last_correct_ids

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
