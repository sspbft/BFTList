"""
Testing functionality of reseting when no other node is resetting. 
Node 0 has gone through a reset without needing it and ended up in phase 1 with RST_PAIR.
Node 0 shall catch up with the other nodes in view (2,2)
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

views = [{"current": -1, "next": 0}, {"current": 2, "next": 2},
         {"current": 2, "next": 2}, {"current": 2, "next": 2},
         {"current": 2, "next": 2}, {"current": 2, "next": 2}]
phases = [1, 0, 0, 0, 0, 0]
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

class TestNodeConvergeAfterReset(AbstractIntegrationTest):
    """Performs health check on all nodes base endpoint (/)."""

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

            for a in asyncio.as_completed(aws):
                result = await a
                data = result["data"]["VIEW_ESTABLISHMENT_MODULE"]
                views = data["views"]
                phases = data["phs"]
                vChange = data["vChange"]
                witnesses = data["witnesses"]
                witnesses_set = data["witnesses_set"]

                vp_target = {"current": 2, "next": 2}
                phases_target = [0 for i in range(N)]

                for i,vp in enumerate(views):
                    checks.append(vp == vp_target)
                checks.append(phases == phases_target)
                checks.append(vChange == False)

            # all checks passed means test passed
            if all(checks):
                test_result = True
                break

            # sleep for 2 seconds and the re-try
            await asyncio.sleep(2)
            calls_left -= 1
            

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