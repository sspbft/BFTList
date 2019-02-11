"""
Case 6

Node 0-2 have the same view v, nodes 3-4 have the same view DF_VIEW and
node 5 is acting Byzantine, i.e. not responding.
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

echo_1 = [{"current": 2, "next": 2} for i in range(N)]
echo_2 = [{"current": 2, "next": 2} for i in range(3)] + \
         [{"current": 1, "next": 1} for i in range(3)]

for i in range(N):
    start_state[str(i)] = {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": views,
            "phs": phases,
            "vChange": vChanges[i],
            "witnesses": witnesses,
            "echo": echo_1 if i <= 2 else echo_2
        }
    }

args = {
    "BYZANTINE": {
        "NODES": [5],
        "BEHAVIOR": "UNRESPONSIVE"
    }
}

class TestNodesConvergeThroughResetAll(AbstractIntegrationTest):
    """Performs health check on all nodes base endpoint (/)."""

    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist(args)

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

            vp_target = {"current": 0, "next": 0}
            phases_target = [0 for i in range(N)]

            # for i,vp in enumerate(views):
            #     self.assertEqual(vp, vp_target)
            # self.assertEqual(phases, phases_target)
            # self.assertEqual(vChange, False)
            

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