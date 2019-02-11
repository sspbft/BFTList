# standard
from abc import ABC, abstractmethod
import unittest
import logging
import warnings

# setup logging for integration tests
FORMAT = "\33[1mIntegrationTest ==> %(name)s : [%(levelname)s]" + \
         " : %(message)s\033[0m"
logging.basicConfig(format=FORMAT, level=logging.NOTSET)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.ERROR)


class AbstractIntegrationTest(unittest.TestCase, ABC):

    pids = []

    def set_pids(self, pids):
        self.pids = pids

    def get_pids(self):
        if not self.pids:
            return []
        return self.pids

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

    @abstractmethod
    def tearDown(self):
        """Force extending classes to implement a tearDown function

        Should ideally kill all launched subprocesses to avoid zombies
        running around.
        """
        pass
