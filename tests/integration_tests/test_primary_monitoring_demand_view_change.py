"""
Case 4 (Primary monitoring)
The systems starts in a safe state but the primary is acting Byzantine and
stops assigning seqnums/stops propagating requests. 

Primary Monitoring should detect and demand a view change of the View Establishment 
Module. After the view is established (new primary is Node 1), the client request
should be assigned sequence numbers and applied.
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
from modules.constants import REQUEST, STATUS, MAXINT, SIGMA, X_SET, REPLY
from modules.enums import ReplicationEnums as enums

# globals
F = 1
N = 6
logger = logging.getLogger(__name__)
start_state = {}

client_req_1 = ClientRequest(0, 0, Operation("APPEND", 1))

for i in range(N):
    start_state[str(i)] = {
        # force stable view_pair for all nodes
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{"current": 0, "next": 0} for i in range(N)]
        },
        "REPLICATION_MODULE": {
            "rep": [
                ReplicaStructure(
                    j,
                    pend_reqs=[client_req_1],
                    prim = 0
                ) for j in range(N)
            ]
        },
        "PRIMARY_MONITORING_MODULE": {
            "prim": 0
        },
        "FAILURE_DETECTOR_MODULE": {
            "prim": 0,
            "cur_check_req":[client_req_1]
        }
    }

args = {
    "BYZANTINE": {
        "NODES": [0],
        "BEHAVIOR": "STOP_ASSIGNING_SEQNUMS"
    }
}

class TestByzStopsAssigningSeqNum(AbstractIntegrationTest):
    """Checks that a Byzantine node can not trick some nodes to do a view change."""

    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist(__name__, args)

    async def validate(self):
        calls_left = helpers.MAX_NODE_CALLS
        test_result = False

        await asyncio.sleep(30)

        while calls_left > 0:
            aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
            checks = []
            last_check = calls_left == 1

            for a in asyncio.as_completed(aws):
                result = await a
                data = result["data"]["REPLICATION_MODULE"]
                id = data["id"]

                if last_check:
                    self.assertEqual(data["rep_state"], [1])
                    self.assertEqual(len(data["r_log"]), 1)
                    self.assertEqual(len(data["pend_reqs"]), 2)                    
                else:
                    checks.append(data["rep_state"] == [1])
                    checks.append(len(data["r_log"]) == 1)
                    checks.append(len(data["pend_reqs"]) == 2)

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