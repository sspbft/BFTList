"""
Case 6.1
The systems starts in a safe state but the primary is acting Byzantine and
stops assigning seqnums/stops propagating requests. No progress should be
made due to primary monitoring module not being included in this test right now.
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
client_req_2 = ClientRequest(0, 1, Operation("APPEND", 2))
client_req_3 = ClientRequest(0, 3, Operation("APPEND", 3))
req_1 = Request(client_req_1, 0, 1)

for i in range(N):
    start_state[str(i)] = {
        "REPLICATION_MODULE": {
            "rep": [
                ReplicaStructure(
                    j,
                    rep_state=[1],
                    r_log=[{REQUEST: req_1, X_SET: {0,1,2,3,4,5}}],
                    pend_reqs=[client_req_2, client_req_3],
                    last_req={0: {REQUEST: req_1, REPLY: [1]}}
                ) for j in range(N)
            ]
        }
    }
for s in start_state:
    start_state[s]["REPLICATION_MODULE"]["rep"][0].set_seq_num(1)

args = {
    "FORCE_VIEW": "0",
    "ALLOW_SERVICE": "1",
    "FORCE_NO_VIEW_CHANGE": "1",
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

        await asyncio.sleep(10)

        while calls_left > 0:
            aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
            checks = []

            for a in asyncio.as_completed(aws):
                result = await a
                data = result["data"]["REPLICATION_MODULE"]
                id = data["id"]
                last_check = calls_left == 1

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