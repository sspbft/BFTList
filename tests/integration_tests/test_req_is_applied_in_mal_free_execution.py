"""
Case 1
There is one request in pending requests that should be propagated through
all different stages before being applied without issue, since no nodes
are acting Byzantine.
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
from modules.constants import REPLY, REQUEST

# globals
F = 1
N = 6
logger = logging.getLogger(__name__)
start_state = {}

req = ClientRequest(0, 189276398, Operation(
    "APPEND",
    1
))

for i in range(N):
    start_state[str(i)] = {
        # force stable view_pair for all nodes
        "VIEW_ESTABLISHMENT_MODULE": {
            "views": [{"current": 0, "next": 0} for i in range(N)]
        },
        "REPLICATION_MODULE": {
            "rep": [
                ReplicaStructure(j, pend_reqs=[req],
                prim=0)
            for j in range(N)]
        }
    }

args = { "FORCE_VIEW": "0", "ALLOW_SERVICE": "1", "FORCE_NO_VIEW_CHANGE": "1" }

class TestReqIsAppliedInMalFreeExecution(AbstractIntegrationTest):
    """Checks that a Byzantine node can not trick some nodes to do a view change."""

    async def bootstrap(self):
        """Sets up BFTList for the test."""
        helpers.write_state_conf_file(start_state)
        return await helpers.launch_bftlist(__name__, N, F, args)

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
                    self.assertEqual(data["rep_state"], [1])
                    self.assertEqual(data["pend_reqs"],[])
                    self.assertTrue(len(data["r_log"]) > 0)
                else:
                    if len(data["r_log"]) == 0:
                        checks.append(False)
                        continue
                    checks.append(data["rep_state"] == [1])
                    checks.append(data["pend_reqs"] == [])
                    checks.append(len(data["r_log"]) > 0)

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