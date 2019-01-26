"""Contains code related to the module resolver."""
from resolve.enums import Function, Module


class Resolver:
    """Module resolver that facilitates communication between modules."""

    def __init__(self):
        """Initializes the resolver."""
        self.modules = None

    def set_modules(self, modules):
        """Sets the modules dict of the resolver."""
        self.modules = modules

    def execute(self, module, func):
        """API for executing a function on a given module."""
        if self.modules is None:
            return -1

        if module == Module.VIEW_ESTABLISHMENT_MODULE:
            return self.view_establishment_exec(func)
        elif module == Module.REPLICATION_MODULE:
            return self.replication_exec(func)
        elif module == Module.PRIMARY_MONITORING_MODULE:
            return self.primary_monitoring_exec(func)
        else:
            raise ValueError("Bad module parameter")

    def view_establishment_exec(self, func):
        """Executes a function on the View Establishment module."""
        module = self.modules[Module.VIEW_ESTABLISHMENT_MODULE]
        if func == Function.GET_VIEW:
            return module.get_view()

    def replication_exec(self, func):
        """Executes a function on the Replication module."""
        raise NotImplementedError

    def primary_monitoring_exec(self, func):
        """Executes a function on the Primary Monitoring module."""
        raise NotImplementedError
