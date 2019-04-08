"""Metrics related to convergence latency of a view establishment."""

# standard
import logging
import time
from prometheus_client import Gauge

logger = logging.getLogger(__name__)

# metrics
convergence_latency = Gauge("convergence_latency",
                            "Execution time of a view establishment",
                            ["node_id", "view"])

# dict to keep track of all client_requests and when they arrived in pending
view_changes = {}


def suspect_prim(cur_view):
    """Called when the Primary Monitoring suspects the primary.

    The event is stored along with the current view in view_changes
    until established() is called with the next view. This enables
    the tracking of the convergence time of a view establishment.
    """
    if cur_view in view_changes:
        logger.error(f"View change from {cur_view} already tracked")
        return
    logger.info(f"Started tracking view change from {cur_view}")
    view_changes[cur_view] = time.time()


def view_established(old_view, node_id):
    """Called whenever a view is established

    The total convergence time is calculated and emitted to the gauge tracking
    the convergence latency time.
    """
    if old_view not in view_changes:
        logger.debug(f"View change from {old_view} not tracked")
        return
    exec_time = time.time() - view_changes[old_view]
    logger.info(f"View change execed in {exec_time} s")

    # emit execution time for this client_req
    convergence_latency.labels(
        node_id,
        old_view,
    ).set(exec_time)

    # stop tracking client_req
    del view_changes[old_view]
