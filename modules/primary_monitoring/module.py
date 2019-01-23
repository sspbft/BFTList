import time
from modules.algorithm_module import AlgorithmModule
from resolver.enums import Function, Module


class PrimaryMonitoringModule:
    def __init__(self, resolver):
        self.resolver = resolver
        self.suspected = False

    def suspected(self):
        return self.suspected

    def run(self):
        while True:
            print("PrimaryMonitoringModule: Calling get_view")
            view = self.resolver.execute(
                module=Module.VIEW_ESTABLISHMENT_MODULE,
                func=Function.GET_VIEW
            )
            print("PrimaryMonitoringModule: Returned view: " + str(view))
            time.sleep(1)
