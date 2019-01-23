from modules.algorithm_module import AlgorithmModule
import time

class ViewEstablishmentModule(AlgorithmModule):
    def __init__(self, resolver):
        self.resolver = resolver
        self.view = 0

    def run(self):
        while True:
            # print(__name__ + ": running")
            time.sleep(3)

    def get_view(self):
        print("ViewEstablishmentModule: call to get_view")
        ret = self.view
        self.view = ret + 1
        return ret