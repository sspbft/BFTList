"""
Case 6
In a very specific setting (See picture on drive) the system can not make progress
and reach a stable state.
Node 0-2 have the same view v, nodes 3-4 have the same view DF_VIEW and
node 5 is acting Byzantine, i.e. not responding.
Node 5 has reported different views to Node 0-2 and node 3-4, so both groups
think that their view is stable.
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

views = [{"current": 2, "next": 2}, {"current": 2, "next": 2},
         {"current": 2, "next": 2}, {"current": DF_VIEW, "next": 0},
         {"current": DF_VIEW, "next": 0}, {"current": 1, "next": 1}]
phases = [0 for i in range(N)]
vChanges = [False for i in range(N)]
witnesses = [False for i in range(N)]
start_state = {}

views = [{"current": 2, "next": 2} for i in range(N)]
views_2 = [{"current": 2, "next": 2} for i in range(3)] + \
         [{"current": DF_VIEW, "next": 0} for i in range(2)] + \
         [{"current": 1, "next": 1}]

for i in range(N):
    start_state[str(i)] = {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": views if i <= 2 else views_2,
            "phs": phases,
            "vChange": vChanges[i],
            "witnesses": witnesses
        }
    }

args = {
    "BYZANTINE": {
        "NODES": [5],
        "BEHAVIOR": "UNRESPONSIVE"
    }
}

class TestByzNodeSilent(AbstractIntegrationTest):
    """Performs health check on all nodes base endpoint (/)."""

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
            last_check = calls_left == 1

            for a in asyncio.as_completed(aws):
                result = await a
                data = result["data"]["VIEW_ESTABLISHMENT_MODULE"]
                views = data["views"]
                id = data["id"]

                for i,vp in enumerate(views):
                    if last_check:
                        if i <= 2:
                            self.assertEqual(vp, {"current": 2, "next": 2})
                        elif i <= 4:
                            self.assertEqual(vp, {"current": -1, "next": 0})
                    else:
                        if i <= 2:
                            checks.append(vp == {"current": 2, "next": 2})
                        elif i <= 4:
                            checks.append(vp == {"current": -1, "next": 0})

            # if all checks passed, test passed
            if all(checks):
                test_result = True
                break

            # sleep for 2 seconds and re-try
            await asyncio.sleep(3)
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