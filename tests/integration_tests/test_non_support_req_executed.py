"""
Case 5
Node 0 has executed an unsupported request, only node 1 has the request in it's req_q.
Node 0 will do a reset and then catch up with the rest of the nodes.
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
from modules.constants import REQUEST, X_SET, STATUS

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

target_rep_state=[1,2]
target_r_log=[
                {REQUEST: req1, X_SET: {0,1,2,3,4,5}},
                {REQUEST: req2, X_SET: {0,1,2,3,4,5}}
                ]

for i in range(N):
    start_state[str(i)] = {
        # force stable view_pair for all nodes
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{"current": 0, "next": 0} for i in range(N)]
        },
        "REPLICATION_MODULE": {
            "rep": [ReplicaStructure(0, rep_state=[1,2,3],
                    r_log=[
                        {REQUEST: req1, X_SET: {0,1,2,3,4,5}},
                        {REQUEST: req2, X_SET: {0,1,2,3,4,5}},
                        {REQUEST: req3, X_SET: {0,1}},
                    ],
                    prim=0
                    ),
                    ReplicaStructure(1, rep_state=target_rep_state,
                    r_log=target_r_log,
                    req_q=[
                        {REQUEST: req3, STATUS: {re.PRE_PREP, re.PREP, re.COMMIT}}
                    ],
                    prim=0
                    )] + [
                    ReplicaStructure(j, rep_state=target_rep_state,
                    r_log=target_r_log,
                    prim=0)
                    for j in range(2,N)]
        }
    }

args = { "FORCE_VIEW": "0", "ALLOW_SERVICE": "1", "FORCE_NO_VIEW_CHANGE": "1" }

class TestNonSupportedReqExecutedAtOneNode(AbstractIntegrationTest):
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
                    self.assertEqual(data["rep_state"], target_rep_state)
                    self.assertEqual(len(data["r_log"]), len(target_r_log))
                else:
                    checks.append(data["rep_state"] == target_rep_state)
                    checks.append(len(data["r_log"]) == len(target_r_log))

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