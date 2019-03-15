"""
Case 2 (Primary monitoring)
The systems starts in a state where a view change is demanded from the Primary Monitoring

The View Establishment should establish the new view 1
"""

# standard
import asyncio
import logging
from copy import deepcopy

# local
from . import helpers
from .abstract_integration_test import AbstractIntegrationTest
from modules.enums import PrimaryMonitoringEnums as enums

# globals
F = 1
N = 6
logger = logging.getLogger(__name__)
start_state = {}

for i in range(2):
    start_state[str(i)] = {
        # force stable view_pair for all nodes
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{"current": 0, "next": 0} for i in range(N)]
        },
        "PRIMARY_MONITORING_MODULE": {
            "prim": 0
        },
        "FAILURE_DETECTOR_MODULE": {
            "prim": 0
        }
    }
for i in range(2,N):
        start_state[str(i)] = {
        # force stable view_pair for all nodes
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{"current": 0, "next": 0} for i in range(N)]
        },
        "PRIMARY_MONITORING_MODULE": {
            "prim": 0,
            "v_status": enums.NO_SERVICE,
            "need_change": True
        },
        "FAILURE_DETECTOR_MODULE": {
            "prim": 0,
            "prim_susp": [False, False, True, True, True, True]
        }
    }
args = {}

class TestPrimMonDemandViewChangeAndViewEstPerformsViewChange(AbstractIntegrationTest):
    """A view change is conducted."""

    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist(__name__, N, F, args)

    async def validate(self):
        calls_left = helpers.MAX_NODE_CALLS
        test_result = False

        await asyncio.sleep(50)

        while calls_left > 0:
            aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
            checks = []
            last_check = calls_left == 1

            for a in asyncio.as_completed(aws):
                result = await a
                data = result["data"]["PRIMARY_MONITORING_MODULE"]

                if last_check:
                    self.assertEqual(data["prim"], 1)
                    self.assertFalse(data["need_change"])             
                else:
                    checks.append(data["prim"] == 1)
                    checks.append(data["need_change"] == False)

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