"""
Case 4

All nodes have stale information (in different variation) except nodes
4, 5 which is up-to-date. All nodes should identify stale information
and move to reset view pair.
"""

# standard
import asyncio
import logging
from copy import deepcopy

# local
from . import helpers
from .abstract_integration_test import AbstractIntegrationTest

# globals
F = 1
N = 6
logger = logging.getLogger(__name__)

views = [{"current": 1, "next": 2}, {"current": 5, "next": 2},
         {"current": 2, "next": 5}, {"current": 2, "next": 2},
         {"current": 0, "next": 0}, {"current": 0, "next": 0}]
phases = [0, 0, 1, 1, 0, 0]
vChanges = [False for i in range(N)]
start_state = {}

for i in range(N):
    start_state[str(i)] = {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": views,
            "phs": phases,
            "vChange": vChanges[i]
        }
    }

class TestNodesConvergeThroughResetAll(AbstractIntegrationTest):
    """Performs health check on all nodes base endpoint (/)."""

    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist()

    async def validate(self):
        """Validates response from / endpoint on all nodes"""
        await asyncio.sleep(20)
        aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
        res = []

        for a in asyncio.as_completed(aws):
            result = await a
            data = result["data"]["VIEW_ESTABLISHMENT_MODULE"]
            views = data["views"]
            phases = data["phs"]
            vChange = data["vChange"]
            witnesses = data["witnesses"]
            witnesses_set = data["witnesses_set"]

            vp_target = {"current": 0, "next": 0}
            phases_target = [0 for i in range(N)]

            for i,vp in enumerate(views):
                self.assertEqual(vp, vp_target)
            self.assertEqual(phases, phases_target)
            self.assertEqual(vChange, False)
            

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