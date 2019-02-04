from abc import ABC, abstractmethod
import unittest
import asyncio

# starting conf - n, f, initial state?
# how to launch - Thor?
# HTTP endpoint to validate target state
# timeout and other settings

class AbstractIntegrationTest(unittest.TestCase, ABC):
    @abstractmethod
    def bootstrap():
        """Bootstraps test.

        This method constructs the environment needed for the test, defined
        needed variables and so on. It should also start the test.
        """
        pass

    @abstractmethod
    def validate():
        """Method for validating target state.
        
        This method is called every self.interval seconds and is used to
        determine if the test has passed. It could for example call an HTTP
        endpoint on each node to validate the state. If the target state has
        not been reached in self.timeout seconds, the test will be marked
        as failed.
        """
        pass

    async def thor(args):
        print("running thor with {args}")
