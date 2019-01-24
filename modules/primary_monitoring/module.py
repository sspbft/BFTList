"""Contains code related to the Primary Monitoring module."""

import time
from resolve.enums import Function, Module


class PrimaryMonitoringModule:
    """Models the Primary Monitoring module."""

    def __init__(self, resolver):
        """Initializes the module."""
        self.resolver = resolver
        self.suspected = False

    def suspected(self):
        """Sample method."""
        return self.suspected

    def run(self):
        """Called whenever the module is launched in a separate thread."""
        while True:
            print("PrimaryMonitoringModule: Calling get_view")
            view = self.resolver.execute(
                module=Module.VIEW_ESTABLISHMENT_MODULE,
                func=Function.GET_VIEW
            )
            print("PrimaryMonitoringModule: Returned view: " + str(view))
            time.sleep(1)
