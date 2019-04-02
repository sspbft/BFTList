"""
Case 5
A corrupted view variable in one node should be detected and converge to the stable view.

Node 0 is behind and has a corrupt next view value. The others are stable in phase 0 and view 2
Node 0 will eventually catch up with the rest of the nodes by adopting their view.
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
            "views": [{"current": 1, "next": 4}, {"current": 2, "next": 2}, {"current": 2, "next": 2}, {"current": 2, "next": 2}, {"current": 2, "next": 2}, {"current": 2, "next": 2}],
            "phs": [1, 0, 0, 0, 0, 0],
            "witnesses": [True for i in range (0, N)],
            "echo": [{"views": {"current": 1, "next": 4} , "phase": 1, "witnesses": True, "vChange": False}] +
                    [{"views": {"current": 2, "next": 2} , "phase": 0, "witnesses": True, "vChange": False} for i in range(0, N-1)]
        }
    },
    "1": {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{"current": 1, "next": 4}] + [{"current": 2, "next": 2} for i in range(0, N-1)],
            "phs": [1, 0, 0, 0, 0, 0],
            "witnesses": [True for i in range (0, N)],
            "echo": [{"views": {"current": 1, "next": 4} , "phase": 1, "witnesses": True, "vChange": False}] +
                    [{"views": {"current": 2, "next": 2} , "phase": 0, "witnesses": True, "vChange": False} for i in range(0, N-1)]
        }
    }
}

for i in range(2, N):
    start_state[str(i)] = deepcopy(start_state["1"])

class TestNodesFollow(AbstractIntegrationTest):
    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist(__name__)

    async def validate(self):
        calls_left = helpers.MAX_NODE_CALLS
        test_result = False

        while calls_left > 0:
            aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
            checks = []
            last_check = calls_left == 1

            for a in asyncio.as_completed(aws):
                result = await a
                views = result["data"]["VIEW_ESTABLISHMENT_MODULE"]["views"]
                target = {"current": 2, "next": 2}

                for vp in views:
                    if last_check:
                        self.assertEqual(vp, target)
                    else:
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