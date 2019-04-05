"""Metrics related to state and requests."""

# standard
import logging
import time
from prometheus_client import Counter, Gauge

# local
from modules.replication.models.client_request import ClientRequest

logger = logging.getLogger(__name__)

PEND = "pend"
START_TIME = "start_time"
MSGS_SENT = "msgs_sent"
BYTES_SENT = "bytes_sent"

# metrics
state_length = Counter("state_length",
                       "Length of the RSM state")

client_req_exec_time = Gauge("client_req_exec_time",
                             "Execution time of client_request",
                             ["client_id", "timestamp", "state_length",
                              "pend_length", "msgs_sent", "bytes_sent",
                              "total_msgs_sent", "total_bytes_sent"])

# dict to keep track of all client_requests and when they arrived in pending
client_reqs = {}


def client_req_added_to_pending(client_req: ClientRequest,
                                start_pend_length,
                                start_msgs_sent,
                                start_bytes_sent):
    """Called whenever a client request is added to pending requests

    The request is stored along with the current timestamp in client_reqs
    until client_req_executed is called for the same request. This enables
    the tracking of client request execution time.
    """
    if client_req in client_reqs:
        logger.error(f"ClientRequest {client_req} already tracked")
        return
    logger.info(f"Started tracking {client_req}")
    client_reqs[client_req] = {START_TIME: time.time(),
                               PEND: start_pend_length,
                               MSGS_SENT: start_msgs_sent,
                               BYTES_SENT: start_bytes_sent}


def client_req_executed(client_req: ClientRequest,
                        state_length,
                        pend_length,
                        msgs_sent,
                        bytes_sent):
    """Called whenever a client request is fully executed, i.e. committed

    The total execution time is calculated and emitted to the gauge tracking
    the client request execution time.
    """
    if client_req not in client_reqs:
        logger.debug(f"ClientRequest {client_req} not tracked")
        return
    exec_time = time.time() - client_reqs[client_req][START_TIME]
    logger.info(f"req execed in {exec_time} s")
    avg_pend_length = (pend_length + client_reqs[client_req][PEND]) / 2
    sent_msg_total = msgs_sent - client_reqs[client_req][MSGS_SENT]
    sent_bytes_total = bytes_sent - client_reqs[client_req][BYTES_SENT]

    # emit execution time for this client_req
    client_req_exec_time.labels(
        client_req.get_client_id(),
        client_req.get_timestamp(),
        state_length,
        avg_pend_length,
        sent_msg_total,
        sent_bytes_total,
        msgs_sent,
        bytes_sent
    ).set(exec_time)

    # stop tracking client_req
    del client_reqs[client_req]
