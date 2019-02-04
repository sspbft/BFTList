from abstract_integration_test import AbstractIntegrationTest
import helpers
import asyncio
import requests

nodes = helpers.get_nodes()
aws = []

class TestHealth(AbstractIntegrationTest):
    """Performs health check on all nodes base endpoint (/)."""

    async def bootstrap(self):
        """Sets up BFTList for the test."""
        await helpers.launch_bftlist()
        await asyncio.sleep(0.5)

    async def validate(self):
        """Validates response from / endpoint on all nodes"""
        aws = [helpers.GET(i, "/") for i in nodes]
        res = []

        for a in asyncio.as_completed(aws):
            result = await a
            res.append(result["status_code"] == 200)

        return all(res)

    def test(self):
        app_process = helpers.run_coro(self.bootstrap())
        result = helpers.run_coro(self.validate())
        self.assertTrue(result)
        helpers.kill(app_process)

if __name__ == '__main__':
    asyncio.run(unittest.main())