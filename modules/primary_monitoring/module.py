"""Contains code related to the Primary Monitoring module."""

# standard
import time
import os
import logging

# local
from modules.algorithm_module import AlgorithmModule
# from resolve.enums import Function, Module
# from modules.enums import PrimaryMonitoringEnums

# global
logger = logging.getLogger(__name__)


class PrimaryMonitoringModule(AlgorithmModule):
    """Models the Primary Monitoring module - View Change algorithm."""

    def __init__(self, id, resolver):
        """Initializes the module."""
        self.resolver = resolver

    def run(self):
        """Called whenever the module is launched in a separate thread."""
        sec = os.getenv("INTEGRATION_TEST_SLEEP")
        time.sleep(int(sec) if sec is not None else 0)

        while True:
            time.sleep(1)

    # Macros
    def clean_state(self):
        """Change each input in vcm to default state."""
        raise NotImplementedError

    def sup_change(self, size_processors):
        """Method description.

        Returns true if the size of set of processors with the same primary
        is size_processors and each memeber have an intersection of
        need_chg_set of at least 3f+1.
        """
        raise NotImplementedError

    # Interface functions
    def no_view_change(self):
        """Returns true if vStatus is OK, meaning it requires no change."""
        raise NotImplementedError

    # Functions added for inter-module communication
    def get_current_view(self, processor_id):
        """Calls get_current_view method at View Establishment module."""
        raise NotImplementedError

    # Functions added for default values
    def get_default_vcm(self):
        """Returns the DEF_STATE for vcm."""
        raise NotImplementedError

    # Function to extract data
    def get_data(self):
        """Returns current values on local variables."""
        return {}
