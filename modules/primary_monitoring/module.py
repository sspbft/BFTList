"""Contains code related to the Primary Monitoring module."""

# standard
import time
import os
import logging

# local
from copy import deepcopy
from modules.algorithm_module import AlgorithmModule
from resolve.enums import Function, Module
from modules.enums import PrimaryMonitoringEnums as enums
from modules.constants import (V_STATUS, PRIM, NEED_CHANGE, NEED_CHG_SET)
from resolve.enums import MessageType
import conf.config as conf
from communication.zeromq.rate_limiter import throttle
from metrics.messages import allow_service_rtt

# global
logger = logging.getLogger(__name__)

# The structure of variable vcm:
# vcm = {v_status: {OK, NO_SERVICE or V_CHANGE},
#       prim: current primary id,
#       need_change: boolean,
#       need_chg_set: set of processors that need change}


class PrimaryMonitoringModule(AlgorithmModule):
    """Models the Primary Monitoring module - View Change algorithm."""

    def __init__(self, id, resolver, n, f):
        """Initializes the module."""
        self.id = id
        self.resolver = resolver
        self.number_of_nodes = n
        self.number_of_byzantine = f
        self.vcm = [{V_STATUS: enums.OK,
                    PRIM: -1,
                    NEED_CHANGE: False,
                    NEED_CHG_SET: set()} for i in range(n)]
        # Metric gathering
        self.allow_service_denied = -1

        if os.getenv("INTEGRATION_TEST"):
            start_state = conf.get_start_state()
            if (start_state is not {} and str(self.id) in start_state and
               "PRIMARY_MONITORING_MODULE" in start_state[str(self.id)]):
                data = start_state[str(self.id)]["PRIMARY_MONITORING_MODULE"]
                if data is not None:
                    if "v_status" in data:
                        self.vcm[self.id][V_STATUS] = deepcopy(
                                                    data["v_status"])
                    if "prim" in data:
                        self.vcm[self.id][PRIM] = deepcopy(data["prim"])
                    if "need_change" in data:
                        self.vcm[self.id][NEED_CHANGE] = deepcopy(
                                                        data["need_change"])
                    if "need_chg_set" in data:
                        self.vcm[self.id][NEED_CHG_SET] = deepcopy(
                                                        data["need_chg_set"])

    def run(self, testing=False):
        """Called whenever the module is launched in a separate thread."""
        sec = os.getenv("INTEGRATION_TEST_SLEEP")
        time.sleep(int(sec) if sec is not None else 0)

        # block until system is ready
        while not testing and not self.resolver.system_running():
            time.sleep(0.1)

        while True:

            if self.vcm[self.id][PRIM] != self.get_current_view(self.id):
                self.clean_state()

            self.vcm[self.id][PRIM] = self.get_current_view(self.id)
            self.vcm[self.id][NEED_CHANGE] = self.resolver.execute(
                                                Module.FAILURE_DETECTOR_MODULE,
                                                Function.SUSPECTED)

            if self.resolver.execute(
               Module.VIEW_ESTABLISHMENT_MODULE, Function.ALLOW_SERVICE):

                # Metrics gathering
                if self.allow_service_denied != -1:
                    latency = time.time() - self.allow_service_denied
                    self.allow_service_denied = -1
                    allow_service_rtt.labels(
                        self.id, self.vcm[self.id][PRIM]).set(latency)

                # Line 9-10
                if (self.vcm[self.id][PRIM] ==
                   self.get_current_view(self.id) and
                   self.vcm[self.id][V_STATUS] != enums.V_CHANGE):
                    self.update_need_chg_set()
                    # Line 11
                    if(self.get_number_of_processors_in_no_service() <
                       (2 * self.number_of_byzantine + 1)):
                        self.vcm[self.id][V_STATUS] = enums.OK
                    # Line 12
                    if(self.vcm[self.id][V_STATUS] == enums.OK and
                       self.sup_change(3 * self.number_of_byzantine + 1)):
                        self.vcm[self.id][V_STATUS] = enums.NO_SERVICE
                    # Line 13
                    elif self.sup_change(4 * self.number_of_byzantine + 1):
                        self.vcm[self.id][V_STATUS] = enums.V_CHANGE
                        logger.debug("Telling ViewEst to change view")
                        self.resolver.execute(
                            Module.VIEW_ESTABLISHMENT_MODULE,
                            Function.VIEW_CHANGE)
                # Line 14
                elif(self.vcm[self.id][PRIM] ==
                     self.get_current_view(self.id) and
                     self.vcm[self.id][V_STATUS] == enums.V_CHANGE):
                    logger.debug("Telling ViewEst to change view")
                    self.resolver.execute(
                            Module.VIEW_ESTABLISHMENT_MODULE,
                            Function.VIEW_CHANGE)
                # Line 15
                else:
                    logger.debug("Cleaning state")
                    self.clean_state()

            # Metric gathering
            else:
                if self.allow_service_denied == -1:
                    self.allow_service_denied = time.time()

            # Stopping the while loop, used for testing purpose
            if testing:
                break

            # Send vcm to all nodes
            self.send_msg()
            throttle()

    # Help functions for run-method
    def get_number_of_processors_in_no_service(self):
        """Returns the number of processors which is in NO_SERVICE."""
        processors = 0
        for processor_vcm in self.vcm:
            if processor_vcm[V_STATUS] == enums.NO_SERVICE:
                processors += 1
        return processors

    def update_need_chg_set(self):
        """Updates the set of processors which requires a change."""
        processor_set = set()
        for processor_id, processor_vcm in enumerate(self.vcm):
            if (processor_vcm[NEED_CHANGE] and
                self.get_current_view(self.id) == self.get_current_view(
                                                        processor_id)):
                processor_set.add(processor_id)

        self.vcm[self.id][NEED_CHG_SET] = deepcopy(processor_set)

    # Macros
    def clean_state(self):
        """Change each input in vcm to default state."""
        self.vcm = [
            self.get_default_vcm(i) for i in range(self.number_of_nodes)]

    def sup_change(self, size_processors):
        """Method description.

        Returns true if the size of set of processors with the same primary
        is size_processors and each memeber have an intersection of
        need_chg_set of at least 3f+1.
        """
        prim_dct = {}

        # Counting how many processors has the same primary
        for processor_id, vcm_tuple in enumerate(self.vcm):
            if vcm_tuple[PRIM] not in prim_dct:
                prim_dct[vcm_tuple[PRIM]] = {processor_id}
            else:
                prim_dct[vcm_tuple[PRIM]].add(processor_id)

        # Get the set that satisify the condition of having equal or more
        # processors than size_processors
        # If there is no such set we will get an empty set
        processor_set = set()
        for k, v in prim_dct.items():
            if len(v) >= size_processors:
                processor_set = v

            # Check the intersection of needChgSet
            need_chg_set_intersection = set()
            for processor_id in processor_set:
                if len(need_chg_set_intersection) == 0:
                    need_chg_set_intersection = self.vcm[
                                                    processor_id][NEED_CHG_SET]
                else:
                    need_chg_set_intersection.intersection(
                        self.vcm[processor_id][NEED_CHG_SET])

            # Check if the intersection is large enough
            if (len(need_chg_set_intersection) >=
                    (3 * self.number_of_byzantine + 1)):
                    return True
        return False

    # Interface functions
    def no_view_change(self):
        """Returns true if vStatus is OK, meaning it requires no change."""
        return (self.vcm[self.id][V_STATUS] == enums.OK)

    # Functions added for inter-module communication
    def get_current_view(self, processor_id):
        """Calls get_current_view method at View Establishment module."""
        return self.resolver.execute(
                                    Module.VIEW_ESTABLISHMENT_MODULE,
                                    Function.GET_CURRENT_VIEW, processor_id)

    # Functions added for default values
    def get_default_vcm(self, id):
        """Returns the DEF_STATE for vcm."""
        return ({V_STATUS: enums.OK,
                PRIM: self.get_current_view(id),
                NEED_CHANGE: False,
                NEED_CHG_SET: set()}
                )

    # Functions to send messages to other nodes

    def send_msg(self):
        """Method description.

        Calls the Resolver to send a message containing the vcm of processor i
        to processor_j
        """
        msg = {
            "type": MessageType.PRIMARY_MONITORING_MESSAGE,
            "sender": self.id,
            "data": {
                    "vcm": deepcopy(self.vcm[self.id]),
                        }
                }
        self.resolver.broadcast(msg)

    def receive_msg(self, msg):
        """Method description.

        Called by the Resolver to recieve a message containing the vcm of
        processor j
        """
        j = msg["sender"]
        if j != self.id:
            self.vcm[j] = deepcopy(msg["data"]["vcm"])

    # Function to extract data
    def get_data(self):
        """Returns current values on local variables."""
        vcm = self.vcm[self.id]
        return {
            "id": self.id,
            "v_status": deepcopy(vcm[V_STATUS].name),
            "prim": deepcopy(vcm[PRIM]),
            "need_change": deepcopy(vcm[NEED_CHANGE]),
            "need_chg_set": deepcopy(vcm[NEED_CHG_SET])
        }
