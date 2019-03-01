"""
Case 3

The replicas does not have a common prefix in replica state, hence find_con_state
should return -1 (indicating something is messed up) and the conflict flag should be
set to True. The nodes will then go through a flushlocal and clean the rep_state and r_log.
"""

# standard
import asyncio
import logging
from copy import deepcopy

# local
from . import helpers
from .abstract_integration_test import AbstractIntegrationTest
from modules.replication.models.replica_structure import ReplicaStructure
from modules.replication.models.client_request import ClientRequest
from modules.replication.models.request import Request
from modules.replication.models.operation import Operation
from modules.enums import ReplicationEnums as re
from modules.constants import REQUEST, X_SET

# globals
F = 1
N = 6
logger = logging.getLogger(__name__)
start_state = {}

req1 = Request((ClientRequest(0, 189276398, Operation(
    "APPEND",
    1
))), 0, 1)
req2 = Request((ClientRequest(0, 189276399, Operation(
    "APPEND",
    2
))), 0, 2)
req3 = Request((ClientRequest(0, 189276402, Operation(
    "APPEND",
    3
))), 0, 3)

for i in range(N):
    start_state[str(i)] = {
        # force stable view_pair for all nodes
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{"current": 0, "next": 0} for i in range(N)]
        },
        "REPLICATION_MODULE": {
            "rep": [
                ReplicaStructure(0, rep_state=[1],r_log=[{REQUEST: req1, X_SET:{0,2,3,5}}], prim=0),
                ReplicaStructure(1, rep_state=[1], r_log=[{REQUEST: req1, X_SET:{1,2,3,0}}], prim=0),
                ReplicaStructure(2, rep_state=[2], r_log=[{REQUEST: req2, X_SET:{1,2,3,4}}], prim=0),
                ReplicaStructure(3, rep_state=[3], r_log=[{REQUEST: req3, X_SET:{0,2,3,5}}], prim=0),
                ReplicaStructure(4, rep_state=[2], r_log=[{REQUEST: req2, X_SET:{0,2,3,4}}], prim=0),
                ReplicaStructure(5, rep_state=[3], r_log=[{REQUEST: req3, X_SET:{0,2,3,5}}], prim=0),
            ]
        }
    }

args = { "FORCE_VIEW": "0", "ALLOW_SERVICE": "1", "FORCE_NO_VIEW_CHANGE": "1" }

class TestNonConsistentRLogLeadToReset(AbstractIntegrationTest):
    """Checks that a Byzantine node can not trick some nodes to do a view change."""

    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist(__name__, args)

    async def validate(self):
        calls_left = helpers.MAX_NODE_CALLS
        test_result = False

        await asyncio.sleep(5)

        while calls_left > 0:
            aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
            checks = []
            last_check = calls_left == 1

            for a in asyncio.as_completed(aws):
                result = await a
                data = result["data"]["REPLICATION_MODULE"]
                id = data["id"]

                # nodes should probably reset their state
                if last_check:
                    self.assertEqual(data["rep_state"], [])
                    self.assertEqual(data["r_log"], [])                    
                else:
                    checks.append(data["rep_state"] == [])
                    checks.append(data["r_log"] == [])

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