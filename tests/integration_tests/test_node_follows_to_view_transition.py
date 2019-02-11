"""
Case 1

Figure 4 in report: A change of view for p_0. 
Enough processors are supporting the view change and will establish the view and then node 0 will follow.
No one is acting Byzantine, but one node is not in the transition phase yet.

The 5 nodes in the transition shall first establish the view and then node 0 will go to a phase 1 and 
transit to view 2.
"""

# standard
import asyncio
import logging
from copy import deepcopy

# local
from . import helpers
from .abstract_integration_test import AbstractIntegrationTest
from resolve.enums import Module

# globals
F = 1
N = 6
logger = logging.getLogger(__name__)

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
    start_state[str(i)] = deepcopy(start_state["1"])

class TestNodesFollow(AbstractIntegrationTest):
    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist()

    async def validate(self):
        calls_left = helpers.MAX_NODE_CALLS
        test_result = False

        while calls_left > 0:
            aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
            target = {"current": 2, "next": 2}

            checks = []
            for a in asyncio.as_completed(aws):
                result = await a
                views = result["data"]["VIEW_ESTABLISHMENT_MODULE"]["views"]
                for vp in views:
                    checks.append(vp == target)

            # if all checks were true, test passed
            if all(checks):
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