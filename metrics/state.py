"""Metrics related to state and requests."""

# standard
import logging
import time
from prometheus_client import Counter, Gauge

# local
from modules.replication.models.client_request import ClientRequest

logger = logging.getLogger(__name__)

# metrics
state_length = Counter("state_length",
                       "Length of the RSM state")

client_req_exec_time = Gauge("client_req_exec_time",
                             "Execution time of client_request",
                             ["client_id", "timestamp"])

# dict to keep track of all client_requests and when they arrived in pending
# structure: { client_req: UNIX timestamp of added to pending }
client_reqs = {}


def client_req_added_to_pending(client_req: ClientRequest):
    """TODO write me."""
    if client_req in client_reqs:
        logger.error(f"ClientRequest {client_req} already tracked")
        return
    logger.info(f"Started tracking {client_req}")
    client_reqs[client_req] = time.time()


def client_req_executed(client_req: ClientRequest):
    """TODO write me."""
    if client_req not in client_reqs:
        logger.error(f"ClientRequest {client_req} not tracked")
        return
    exec_time = time.time() - client_reqs[client_req]
    logger.info(f"req execed in {exec_time} s")

    # emit execution time for this client_req
    client_req_exec_time.labels(
        client_req.get_client_id(),
        client_req.get_timestamp()
    ).set(exec_time)

    # stop tracking client_req
    del client_reqs[client_req]
