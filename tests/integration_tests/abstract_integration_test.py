from abc import ABC, abstractmethod
import unittest

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

BLUE = "\033[94m"
ENDC = "\033[0m"

class AbstractIntegrationTest(unittest.TestCase, ABC):
    @abstractmethod
    def bootstrap(self):
        """Bootstraps test.

        This method constructs the environment needed for the test, defined
        needed variables and so on. It should also start the test.
        """
        pass

    @abstractmethod
    def validate(self):
        """Method for validating target state.
        
        This method is called every self.interval seconds and is used to
        determine if the test has passed. It could for example call an HTTP
        endpoint on each node to validate the state. If the target state has
        not been reached in self.timeout seconds, the test will be marked
        as failed.
        """
        pass

    def log(self, msg):
        if msg:
            print(f"{BLUE}IntegrationTest.log ==> {msg}{ENDC}")
