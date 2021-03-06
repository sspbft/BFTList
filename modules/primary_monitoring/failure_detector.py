"""Contains code related to the Primary Monitoring module."""

# standard
import logging
from copy import deepcopy
import time
import os

# local
from resolve.enums import Function, Module
from modules.constants import (CNT_THRESHOLD, BEAT_THRESHOLD, VIEW_CHANGE)
from resolve.enums import MessageType
from queue import Queue
import conf.config as conf
from communication.zeromq.rate_limiter import throttle
import modules.byzantine as byz

# globals
logger = logging.getLogger(__name__)


class FailureDetectorModule:
    """Models the Primary Monitoring module - Failure detector algorithm."""

    first_run = True

    def __init__(self, id, resolver, n, f):
        """Initializes the module."""
        self.resolver = resolver
        self.id = id
        self.number_of_nodes = n
        self.number_of_byzantine = f
        self.beat = [0 for i in range(n)]
        self.cnt = 0
        self.prim_susp = [False for i in range(n)]
        self.cur_check_req = []
        self.fd_set = set()
        self.prim = -1
        self.msg_queue = Queue()
        self.was_unresponsive = False

        # Injection of starting state for integration tests
        if os.getenv("INTEGRATION_TEST") or os.getenv("INJECT_START_STATE"):
            start_state = conf.get_start_state()
            if (start_state is not {} and str(self.id) in start_state and
               "FAILURE_DETECTOR_MODULE" in start_state[str(self.id)]):
                data = start_state[str(self.id)]["FAILURE_DETECTOR_MODULE"]
                if data is not None:
                    logger.warning("Injecting start state")
                    if "beat" in data:
                        self.beat = deepcopy(data["beat"])
                    if "cnt" in data:
                        self.cnt = deepcopy(data["cnt"])
                    if "prim_susp" in data:
                        self.prim_susp = deepcopy(data["prim_susp"])
                    if "cur_check_req" in data:
                        self.cur_check_req = deepcopy(data["cur_check_req"])
                    if "prim" in data:
                        self.prim = deepcopy(data["prim"])

    def run(self, testing=False):
        """Called whenever the module is launched in a separate thread."""
        # block until system is ready
        while not testing and not self.resolver.system_running():
            time.sleep(0.1)

        while True:
            if (byz.is_byzantine() and
               byz.get_byz_behavior() == byz.UNRESPONSIVE):
                self.was_unresponsive = True

            if self.msg_queue.empty():
                time.sleep(0.1)
            else:
                msg = self.msg_queue.get()
                processor_j = msg["sender"]
                prim_susp_j = msg["data"]["prim_susp"]
                self.upon_token_from_pj(processor_j, prim_susp_j)
                self.send_msg(processor_j)

            if testing:
                break

            # When first run, send a message to everyone
            # After the first run, send message to nodes as they send a
            # message to you
            if (self.first_run or
               (not byz.is_byzantine() and self.was_unresponsive)):
                self.was_unresponsive = False
                nodes = conf.get_nodes()
                for node_j, _ in nodes.items():
                    if node_j != self.id:
                        self.send_msg(node_j)
                self.first_run = False

            throttle()

    def upon_token_from_pj(self, processor_j: int, prim_susp_j):
        """Checks responsiveness and liveness of processor j."""
        # Line 9-11
        self.update_beat(processor_j)

        # Line 13-14
        new_prim = self.get_current_view(self.id)
        if self.prim != new_prim:
            self.reset()
        self.prim = new_prim
        if self.allow_service() and self.resolver.execute(
                                        Module.PRIMARY_MONITORING_MODULE,
                                        Function.NO_VIEW_CHANGE):
            if self.prim == processor_j:
                self.check_progress_by_prim(processor_j)
            elif (self.prim == self.get_current_view(processor_j)):
                self.prim_susp[processor_j] = prim_susp_j
            # Ignoring the for each node \ prim reset cnt, has only one value
            if self.prim == self.id:
                self.cnt = 0
            if(not self.prim_susp[self.id]):
                beat_abv_thresh = self.prim not in self.fd_set
                cntr_abv_thresh = self.cnt > CNT_THRESHOLD
                self.prim_susp[self.id] = beat_abv_thresh or cntr_abv_thresh
                if beat_abv_thresh:
                    logger.debug("Suspecting unresponsive primary")
                if cntr_abv_thresh:
                    logger.debug("Suspecting non-progressing primary")

        elif not self.allow_service():
            self.reset()

    # Macros
    def reset(self):
        """Resets local variables."""
        logger.debug("Reset Failure Detector")
        self.beat = [0 for i in range(self.number_of_nodes)]
        self.cnt = 0
        self.prim_susp = [False for i in range(self.number_of_nodes)]
        self.cur_check_req = []

    # Interface functions
    def suspected(self):
        """Returns true if the processor suspects the primary to be faulty."""
        num_of_processor = 0

        for processor_id in range(self.number_of_nodes):
            if (self.prim_susp[processor_id] and
               self.get_current_view(processor_id) ==
                    self.get_current_view(self.id)):
                num_of_processor += 1
        if num_of_processor >= (self.number_of_nodes - 2 *
                                self.number_of_byzantine):
            return True
        return False

    # Functions added for inter-module communication
    def get_current_view(self, processor_id):
        """Calls get_current_view method at View Establishment module."""
        # Mock if non self-stablizing:
        if os.getenv("NON_SELF_STAB"):
            return 0
        else:
            return self.resolver.execute(Module.VIEW_ESTABLISHMENT_MODULE,
                                         Function.GET_CURRENT_VIEW,
                                         processor_id)

    def get_pend_reqs(self):
        """Calls get_pend_reqs in Replication module"""
        pend_reqs = deepcopy(self.resolver.execute(
                        Module.REPLICATION_MODULE,
                        Function.GET_PEND_REQS))
        if pend_reqs == VIEW_CHANGE:
            # There has been a view_change
            # The replication module takes care to check the progress of the
            # new primary
            # Hence this module can "accept" the progress
            return []
        else:
            return pend_reqs

    def allow_service(self):
        """Calls allow_service in View Establishment module"""
        # Mock if non self-stablizing:
        if os.getenv("NON_SELF_STAB"):
            return True
        else:
            return self.resolver.execute(Module.VIEW_ESTABLISHMENT_MODULE,
                                         Function.ALLOW_SERVICE)

    # Added functions
    def check_progress_by_prim(self, prim):
        """Checks for progress done by the primary.

        Line 15-19
        """
        # Check progress
        exist_progress = False
        if len(self.cur_check_req) == 0:
            exist_progress = True
        else:
            for req in self.cur_check_req:
                if req not in self.get_pend_reqs():
                    exist_progress = True
                    break
        # If there has been progress, reset the cnt
        if exist_progress:
            self.cnt = 0
            self.cur_check_req = deepcopy(self.get_pend_reqs())
        # The primary has not made progress, increase our own counter
        else:
            self.cnt += 1

    def update_beat(self, processor_j):
        """Responsive check of processor_j.

        Line 9-11
        """
        self.beat[processor_j] = 0
        self.beat[self.id] = 0

        new_fd_set = {processor_j, self.id}
        for other_processor in range(self.number_of_nodes):
            if other_processor == self.id or other_processor == processor_j:
                continue
            self.beat[other_processor] += 1
            if self.beat[other_processor] < BEAT_THRESHOLD:
                new_fd_set.add(other_processor)
        self.fd_set = deepcopy(new_fd_set)

    # Functions to send messages to other nodes

    def send_msg(self, processor_j):
        """Method description.

        Calls the Resolver to send a message containing the vcm of processor i
        to processor_j
        """
        msg = {
            "type": MessageType.FAILURE_DETECTOR_MESSAGE,
            "sender": self.id,
            "data": {
                    "prim_susp": self.prim_susp[self.id],
                        }
                }
        self.resolver.send_to_node(processor_j, msg, fd_msg=True)

    def receive_msg(self, msg):
        """Method description.

        Called by the Resolver to recieve a message containing the vcm of
        processor j
        """
        self.msg_queue.put(msg)

    # Function to extract data
    def get_data(self):
        """Returns current values on local variables."""
        return {
            "id": self.id,
            "beat": deepcopy(self.beat),
            "cnt": deepcopy(self.cnt),
            "prim_susp": deepcopy(self.prim_susp),
            "cur_check_req": deepcopy(self.cur_check_req),
            "prim_fd": deepcopy(self.prim)
        }
