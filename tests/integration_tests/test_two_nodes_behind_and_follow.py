"""
Case 1.1

Two nodes are behind so there is not enough node yet to establish view 2.
We want the nodes to catch up with the majority of nodes.
Node 0 and 1 will catch up to phase 1 and hence moving into view 2.
Then view 2 will be establishable and all nodes will establish the view (2,2)
The system will be in a safe state in phase 0, view 2.
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
            "echo": [{"views": {CURRENT: 1, NEXT: 1} , "phase": 0, "witnesses": True, "vChange": False} for i in range(0,N)]}
    },
    "1": {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{CURRENT: 1, NEXT: 1}] + [{CURRENT: 1, NEXT: 1}] + [{CURRENT: 1, NEXT: 2} for i in range(0, N-2)],
            "phs": [0, 0, 1, 1, 1, 1],
            "witnesses": [True for i in range (0, N)],
            "echo": [{"views": {CURRENT: 1, NEXT: 1} , "phase": 0, "witnesses": True, "vChange": False} for i in range(0,N)]
        }
    },
    "2": {
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{CURRENT: 1, NEXT: 1}] + [{CURRENT: 1, NEXT: 1}] + [{CURRENT: 1, NEXT: 2} for i in range(0, N-2)],
            "phs": [0, 0, 1, 1, 1, 1],
            "witnesses": [True for i in range (0, N)],
            "echo": [{"views": {CURRENT: 1, NEXT: 2} , "phase": 1, "witnesses": True, "vChange": False} for i in range(0, N)]
        }
    }
}

for i in range(3, N):
    start_state[str(i)] = start_state["2"]

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
                for vp in views:
                    if last_check:
                        self.assertEqual(vp, {CURRENT: 2, NEXT: 2})
                    else:
                        checks.append(vp == {CURRENT: 2, NEXT: 2})

            # all checks passing means test has passed
            if all(checks):
                test_result = True
                break

            # wait 2 seconds and then re-try
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