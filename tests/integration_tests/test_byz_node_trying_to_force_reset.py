"""
Case 7.2
Byzantine node 0 tells all nodes that its view is RST_PAIR,
trying to force the others to do a reset, eventhough it is not needed.
All correct nodes should stay in the current view (1,1) since not enough nodes seems
to be wanting a reset. Meaning the Byz node should NOT be able to trick
the correct nodes into a reset.
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
DF_VIEW = 0
logger = logging.getLogger(__name__)

views = [{"current": 1, "next": 1} for i in range(N)]
phases = [0 for i in range(N)]
vChanges = [False for i in range(N)]
witnesses = [True for i in range(N)]
start_state = {}

views = [{"current": 1, "next": 1} for i in range(N)]

for i in range(N):
    start_state[str(i)] = {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": views,
            "phs": phases,
            "vChange": vChanges[i],
            "witnesses": witnesses
        }
    }

args = {
    "BYZANTINE": {
        "NODES": [0],
        "BEHAVIOR": "FORCING_RESET"
    }
}

class TestByzNodeForcingReset(AbstractIntegrationTest):
    """Testing so Byzantine node can not force an unnecessary reset."""

    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist(__name__, args)

    async def validate(self):
        calls_left = helpers.MAX_NODE_CALLS
        test_result = False

        # sleep for 10 seconds, then check if no progress has been made
        await asyncio.sleep(10)

        while calls_left > 0:
            aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
            checks = []

            for a in asyncio.as_completed(aws):
                result = await a
                data = result["data"]["VIEW_ESTABLISHMENT_MODULE"]
                views = data["views"]
                id = data["id"]
                last_check = calls_left == 1
                target = {"current": 1, "next": 1}

                if id != 0:
                    for i,vp in enumerate(views):
                        if i > 0:
                            if last_check:
                                self.assertEqual(vp, target)
                            else:
                                checks.append(vp == target)

            # if all checks passed, test passed
            if all(checks):
                test_result = True
                break

            # sleep for 2 seconds and re-try
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