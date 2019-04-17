"""
Bounded rLog invariant
Node 5 has executed req 0 => rep_state = [0]
Node 0-4 has executed req 17 => rep_state = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
This means that node 5 is 19 behind
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

client_reqs = [ClientRequest(0, i, Operation("APPEND", i)) for i in range(20)]
reqs = [Request(client_reqs[i], 0, i) for i in range(20)] 
r_logs = [{REQUEST: reqs[i], X_SET: {0,1,2,3,4}} for i in range(20)]

for i in range(N):
    start_state[str(i)] = {
        "REPLICATION_MODULE": {
            "rep": [
                ReplicaStructure(
                    j,
                    rep_state=[k for k in range(20)],
                    r_log=r_logs[-15:],
                    pend_reqs=[]
                ) for j in range(N-1)
            ] + [
                ReplicaStructure(
                    5,
                    rep_state=[0],
                    r_log=[r_logs[0]],
                    pend_reqs=[]
                )
            ]
        }
    }
for s in start_state:
    start_state[s]["REPLICATION_MODULE"]["rep"][0].set_seq_num(17)

args = {
    "FORCE_VIEW": "0",
    "ALLOW_SERVICE": "1",
    "FORCE_NO_VIEW_CHANGE": "1",
}

class TestNodeBehindRLog(AbstractIntegrationTest):
    """Checks that a node can catch up with bounded rLog."""

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
                data = result["data"]["REPLICATION_MODULE"]
                id = data["id"]

                if last_check:
                    self.assertEqual(data["rep_state"], [i for i in range(20)])
                    self.assertEqual(len(data["r_log"]), 15)
                else:
                    checks.append(data["rep_state"] == [i for i in range(20)])
                    checks.append(len(data["r_log"]) == 15)

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