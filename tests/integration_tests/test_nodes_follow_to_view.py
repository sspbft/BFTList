"""TODO write description for test."""

import helpers
import asyncio

from abstract_integration_test import AbstractIntegrationTest
from resolve.enums import Module

F = 1
N = 6

start_state = {
    "0": {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{"current": 1, "next": 1}, {"current": 1, "next": 2}, {"current": 1, "next": 2}, {"current": 1, "next": 2}, {"current": 1, "next": 2}, {"current": 1, "next": 2}],
            "phs": [0, 1, 1, 1, 1, 1],
            "witnesses": [True for i in range (0, N)],
            "echo": [{"views": {"current": 1, "next": 1} , "phase": 0, "witnesses": True}] +
                    [{"views": {"current": 1, "next": 2} , "phase": 1, "witnesses": True} for i in range(0, N-1)]
        }
    },
    "1": {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{"current": 1, "next": 1}] + [{"current": 1, "next": 2} for i in range(0, N-1)],
            "phs": [0, 1, 1, 1, 1, 1],
            "witnesses": [True for i in range (0, N)],
            "echo": [{"views": {"current": 1, "next": 1} , "phase": 0, "witnesses": True}] +
                    [{"views": {"current": 1, "next": 2} , "phase": 1, "witnesses": True} for i in range(0, N-1)]
        }
    }
}

for i in range(2, N):
    start_state[str(i)] = start_state["1"]

class TestNodesFollow(AbstractIntegrationTest):
    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist()

    async def validate(self):
        """Validates response from / endpoint on all nodes"""
        await asyncio.sleep(10)
        aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
        res = {}
        target = {"current": 2, "next": 2}

        # waits for all health check calls to complete
        for a in asyncio.as_completed(aws):
            result = await a
            views = result["data"]["VIEW_ESTABLISHMENT_MODULE"]["views"]
            for vp in views:
                self.assertEqual(vp, target)

    def test(self):
        super().log(f"{__name__} starting")
        pids = helpers.run_coro(self.bootstrap())
        helpers.run_coro(self.validate())
        helpers.kill(pids)
        helpers.cleanup()
        super().log(f"{__name__} finished")

if __name__ == '__main__':
    asyncio.run(unittest.main())