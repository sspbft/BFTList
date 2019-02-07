"""
Two nodes are behind, there is not enough node to establish view 2.
Node 0 and 1 will catch up to phase 1 for moving into view 2.
Then all will establish view 2 and the system will be in a safe state in phase 0, view 2.
"""

# standard
import asyncio
import logging

# local
from . import helpers
from .abstract_integration_test import AbstractIntegrationTest
from resolve.enums import Module
from modules.enums import ViewEstablishmentEnums as venum
from modules.constants import CURRENT, NEXT

# globals
F = 1
N = 6
logger = logging.getLogger(__name__)

start_state = {
    "0": {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{CURRENT: 1, NEXT: 1}] + [{CURRENT: 1, NEXT: 1}] + [{CURRENT: 1, NEXT: 2} for i in range(0, N-2)],
            "phs": [0, 0, 1, 1, 1, 1],
            "witnesses": [True for i in range (0, N)],
            "echo": [{"views": {CURRENT: 1, NEXT: 1} , "phase": 0, "witnesses": True} for i in range(0,N)]}
    },
    "1": {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{CURRENT: 1, NEXT: 1}] + [{CURRENT: 1, NEXT: 1}] + [{CURRENT: 1, NEXT: 2} for i in range(0, N-2)],
            "phs": [0, 0, 1, 1, 1, 1],
            "witnesses": [True for i in range (0, N)],
            "echo": [{"views": {CURRENT: 1, NEXT: 1} , "phase": 0, "witnesses": True} for i in range(0,N)]
        }
    },
    "2": {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{CURRENT: 1, NEXT: 1}] + [{CURRENT: 1, NEXT: 1}] + [{CURRENT: 1, NEXT: 2} for i in range(0, N-2)],
            "phs": [0, 0, 1, 1, 1, 1],
            "witnesses": [True for i in range (0, N)],
            "echo": [{"views": {CURRENT: 1, NEXT: 2} , "phase": 1, "witnesses": True} for i in range(0, N)]
        }
    }
}

for i in range(3, N):
    start_state[str(i)] = start_state["2"]

class TestNodesFollow(AbstractIntegrationTest):
    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist()

    async def validate(self):
        """Validates response from / endpoint on all nodes"""
        await asyncio.sleep(20)
        aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
        res = {}
        target = {CURRENT: 2, NEXT: 2}

        # waits for all health check calls to complete
        for a in asyncio.as_completed(aws):
            result = await a
            views = result["data"]["VIEW_ESTABLISHMENT_MODULE"]["views"]
            for vp in views:
                self.assertEqual(vp, target)

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