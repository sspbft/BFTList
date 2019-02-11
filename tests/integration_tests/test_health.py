"""
Makes sure nodes start up correctly and serve the /data endpoint
"""

# standard
import asyncio
import logging

# local
from . import helpers
from .abstract_integration_test import AbstractIntegrationTest

logger = logging.getLogger(__name__)

class TestHealth(AbstractIntegrationTest):
    """Performs health check on all nodes base endpoint (/)."""

    async def bootstrap(self):
        """Sets up BFTList for the test."""
        return await helpers.launch_bftlist()

    async def validate(self):
        """Validates response from / endpoint on all nodes
        
        This method runs for at most helpers.MAX_NODE_CALLS times, then it
        will fail the test if target state is not reached.
        """
        calls_left = helpers.MAX_NODE_CALLS
        test_result = False

        while calls_left > 0:
            aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
            res = []

            # waits for all health check calls to complete
            for a in asyncio.as_completed(aws):
                result = await a
                res.append(result["status_code"] == 200)

            # if all checks were true, test passed
            if all(res):
                test_result = True
                break

            # sleep for 2 seconds and then re-try
            await asyncio.sleep(2)
            calls_left -= 1
        self.assertTrue(test_result)

    @helpers.suppress_warnings
    def test(self):
        logger.info(f"{__name__} starting")
        pids = helpers.run_coro(self.bootstrap())
        super().set_pids(pids)

        helpers.run_coro(self.validate())
        logger.info(f"{__name__} finished")

    def tearDown(self):
        helpers.kill(super().get_pids())
        helpers.cleanup()

if __name__ == '__main__':
    asyncio.run(unittest.main())