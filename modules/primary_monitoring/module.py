"""Contains code related to the Primary Monitoring module."""

# standard
import time
import os
import logging

# local
from modules.algorithm_module import AlgorithmModule
from resolve.enums import Function, Module
from modules.enums import PrimaryMonitoringEnums as enums
from modules.constants import V_STATUS, PRIM, NEED_CHANGE, NEED_CHG_SET

# global
logger = logging.getLogger(__name__)

# vcm = {v_status: OK, NO_SERVICE or V_CHANGE,
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
        self.vcm = [self.get_default_vcm(id) for i in range(n)]

    def run(self):
        """Called whenever the module is launched in a separate thread."""
        sec = os.getenv("INTEGRATION_TEST_SLEEP")
        time.sleep(int(sec) if sec is not None else 0)

        while True:
            time.sleep(1)

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
        return (len(need_chg_set_intersection) >=
                (3 * self.number_of_byzantine + 1))

    # Interface functions
    def no_view_change(self):
        """Returns true if vStatus is OK, meaning it requires no change."""
        return (self.vcm[self.id][V_STATUS] == enums.OK)

    # Functions added for inter-module communication
    def get_current_view(self, processor_id):
        """Calls get_current_view method at View Establishment module."""
        return self.resolver.execute(
                                    Module.VIEW_ESTABLISHMENT_MODULE,
                                    Function.GET_CURRENT_VIEW, id)

    # Functions added for default values
    def get_default_vcm(self, id):
        """Returns the DEF_STATE for vcm."""
        return ({V_STATUS: enums.OK,
                PRIM: self.get_current_view(id),
                NEED_CHANGE: False,
                NEED_CHG_SET: set()}
                )

    # Function to extract data
    def get_data(self):
        """Returns current values on local variables."""
        return {}
