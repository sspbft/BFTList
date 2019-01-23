from resolver.enums import Function, Module


class Resolver:
    def __init__(self):
        self.modules = None

    def set_modules(self, modules):
        self.modules = modules

    def execute(self, module, func):
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
        module = self.modules[Module.VIEW_ESTABLISHMENT_MODULE]
        if func == Function.GET_VIEW:
            return module.get_view()

    def replication_exec(self, func):
        raise NotImplementedError

    def primary_monitoring_exec(self, func):
        raise NotImplementedError
