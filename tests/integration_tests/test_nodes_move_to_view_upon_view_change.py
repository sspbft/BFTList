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

start_state = {
    "0": {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{"current": 1, "next": 1} for i in range(N)],
            "vChange": True,
            "phs": [0 for i in range(N)]
        }
    }
}

for i in range(1, N):
    start_state[str(i)] = deepcopy(start_state["0"])
start_state["5"]["VIEW_ESTABLISHMENT_MODULE"]["vChange"] = False

class TestNodeMovesToViewOnViewChange(AbstractIntegrationTest):
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
            data = result["data"]
            views = data["VIEW_ESTABLISHMENT_MODULE"]["views"]
            vp_target = {"current": 2, "next": 2}

            for i,vp in enumerate(views):
                if i == 5:
                    self.assertEqual(vp, vp_target)
                else:
                    self.assertIn(vp, [vp_target, {"current": 1, "next": 1}])

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