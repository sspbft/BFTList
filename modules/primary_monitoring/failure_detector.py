"""Contains code related to the Primary Monitoring module."""

import time
# from resolve.enums import Function, Module
# from modules.enums import PrimaryMonitoringEnums


class PrimaryMonitoringModule:
    """Models the Primary Monitoring moduel - Failure detector algorithm."""

    def __init__(self, resolver, ):
        """Initializes the module."""
        self.resolver = resolver

    def run(self):
        """Called whenever the module is launched in a separate thread."""
        while True:
            time.sleep(1)

    # Macros
    def reset(self):
        """Resets local variables."""
        raise NotImplementedError

    # Interface functions
    def suspected(self):
        """Returns true if the processor suspects the primary to be faulty."""
        raise NotImplementedError

    # Functions added for inter-module communication
    def get_view(self, processor_id):
        """Calls get_view method at View Establishment module."""
        raise NotImplementedError
