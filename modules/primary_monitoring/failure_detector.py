"""Contains code related to the Primary Monitoring module."""

import time
from resolve.enums import Function, Module
# from modules.enums import PrimaryMonitoringEnums


class FailureDetectorModule:
    """Models the Primary Monitoring moduel - Failure detector algorithm."""

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

    def run(self):
        """Called whenever the module is launched in a separate thread."""
        # TODO change while to upon token.
        while True:
            time.sleep(1)

        # After line 14, meaning if j == prim:
            # Call self.check_progress_by_prim(j)

        # else:
            # continue here

    # Macros
    def reset(self):
        """Resets local variables."""
        self.beat = [0 for i in range(self.number_of_nodes)]
        self.cnt = 0
        self.prim_susp = [False for i in range(self.number_of_nodes)]
        self.cur_check_req = []

    # Interface functions
    def suspected(self):
        """Returns true if the processor suspects the primary to be faulty."""
        num_of_processor = 0

        for processor_id in range(self.number_of_nodes):
            if (self.get_current_view(processor_id) ==
                    self.get_current_view(self.id) and
               self.prim_susp[processor_id]):
                num_of_processor += 1
        if num_of_processor >= (3 * self.number_of_byzantine + 1):
            return True
        return False

    # Functions added for inter-module communication
    def get_current_view(self, processor_id):
        """Calls get_current_view method at View Establishment module."""
        return self.resolver.execute(Module.VIEW_ESTABLISHMENT_MODULE,
                                     Function.GET_CURRENT_VIEW, processor_id)

    def get_pend_reqs(self):
        """Calls get_pend_reqs in Replication module"""
        return self.resolver.execute(Module.REPLICATION_MODULE,
                                     Function.GET_PEND_REQS)

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
            self.cur_check_req = self.get_pend_reqs()
        # The primary has not made progress, increase our own counter
        else:
            self.cnt += 1
