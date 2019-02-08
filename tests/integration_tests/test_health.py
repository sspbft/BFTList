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
        """Validates response from / endpoint on all nodes"""
        aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
        res = []

        # waits for all health check calls to complete
        for a in asyncio.as_completed(aws):
            result = await a
            res.append(result["status_code"] == 200)

        self.assertTrue(all(res))

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