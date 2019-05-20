"""
Case 1 (Primary monitoring)
The systems starts in a state where there is stale information of different kind.

Node 1 has a corrupt injected beat-value
Node 2 has a corrupt injected cnt-value
Node 3-4 has corrupt prim_susp value
Node 5 has corrupt cur_check_reqs so that it will think primary is doing progress

Nodes should suspect the primary since a node never "unsuspect" a primary until there
has been a view change.

NOTE: View Establishment is going crazy in this test, since we are mocking the get_current_view
for the Primary Monitoring/Failure detector. The FD never sees a view change even if the VE is doing it
This is because we are just testing PM/FD and not VE for this test.
"""

# standard
import asyncio
import logging
from copy import deepcopy

# local
from . import helpers
from .abstract_integration_test import AbstractIntegrationTest
from modules.replication.models.client_request import ClientRequest
from modules.replication.models.request import Request
from modules.replication.models.operation import Operation
from modules.enums import PrimaryMonitoringEnums as enums

# globals
F = 1
N = 6
logger = logging.getLogger(__name__)
start_state = {}

client_req_1 = ClientRequest(0, 0, Operation("APPEND", 1))

for i in range(N):
    start_state[str(i)] = {
        "PRIMARY_MONITORING_MODULE": {
            "prim": 0
        },
        "FAILURE_DETECTOR_MODULE": {
            "prim": 0
        }
    }
start_state[1] = {
        "PRIMARY_MONITORING_MODULE": {
            "prim": 0
        },
        "FAILURE_DETECTOR_MODULE": {
            "prim": 0,
            "beat": [55, 0, 0, 0, 0, 0]
        }
    }
start_state[2] = {
        "PRIMARY_MONITORING_MODULE": {
            "prim": 0
        },
        "FAILURE_DETECTOR_MODULE": {
            "prim": 0,
            "cnt": 35
        }
    }
for i in range(3,5):
    start_state[i] = {
            "PRIMARY_MONITORING_MODULE": {
                "prim": 0
            },
            "FAILURE_DETECTOR_MODULE": {
                "prim": 0,
                "prim_susp": [False, False, False, True, True, False]
            }
        }
start_state[5] = {
        "PRIMARY_MONITORING_MODULE": {
            "prim": 0
        },
        "FAILURE_DETECTOR_MODULE": {
            "prim": 0,
            "cur_check_req": [client_req_1]
        }
    }
args = {
    "FORCE_VIEW": "0",
    "ALLOW_SERVICE": "1",
}

class TestPrimaryMonitoringStaleDataViewChangeDemand(AbstractIntegrationTest):
    """Checks that a Byzantine node can not trick some nodes to do a view change."""

    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist(__name__, N, F, args)

    async def validate(self):
        calls_left = helpers.MAX_NODE_CALLS
        test_result = False

        await asyncio.sleep(10)

        while calls_left > 0:
            aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
            checks = []
            last_check = calls_left == 1

            for a in asyncio.as_completed(aws):
                result = await a
                data = result["data"]["PRIMARY_MONITORING_MODULE"]
                id = data["id"]

                if last_check:
                    self.assertEqual(data["v_status"], "V_CHANGE" or
                                     data["v_status"] == "NO_SERVICE")
                    self.assertEqual(data["need_change"], True)                  
                else:
                    checks.append(data["v_status"] == "V_CHANGE" or
                                  data["v_status"] == "NO_SERVICE")
                    checks.append(data["need_change"] == True)

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