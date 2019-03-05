"""
Case 1 (Primary monitoring)
The systems starts in a state where there is stale information of different kind.

Node 1 has a corrupt injected beat-value
Node 2 has a corrupt injected cnt-value
Node 3-4 has corrupt prim_susp value
Node 5 has corrupt cur_check_reqs so that it will think primary is doing progress

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
            "beat": [15, 0, 0, 0, 0, 0]
        }
    }
start_state[2] = {
        "PRIMARY_MONITORING_MODULE": {
            "prim": 0
        },
        "FAILURE_DETECTOR_MODULE": {
            "prim": 0,
            "cnt": 15
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
    "BYZANTINE": {
        "NODES": [0],
        "BEHAVIOR": "STOP_ASSIGNING_SEQNUMS"
    }
}

class TestPrimaryMonitoringStaleDataRemoved(AbstractIntegrationTest):
    """Checks that a Byzantine node can not trick some nodes to do a view change."""

    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist(__name__, args)

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
                data = result["data"]["PRIMARY_MONITORING"]
                id = data["id"]

                if last_check:
                    self.assertEqual(data["cnt"], 0)
                    self.assertEqual(len(data["beat"][0]), 0)                  
                else:
                    checks.append(data["cnt"] == 0)
                    checks.append(len(data["beat"][0]) == 0)

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