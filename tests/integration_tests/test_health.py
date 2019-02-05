import asyncio
import helpers

from abstract_integration_test import AbstractIntegrationTest

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
        super().log(f"{__name__} starting")
        pids = helpers.run_coro(self.bootstrap())
        helpers.run_coro(self.validate())
        helpers.kill(pids)
        helpers.cleanup()
        super().log(f"{__name__} finished")

if __name__ == '__main__':
    asyncio.run(unittest.main())