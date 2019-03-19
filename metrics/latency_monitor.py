"""Module containing a latency monitor used for latency metrics."""

# standard
import subprocess
import os
import logging

# local
from conf.config import get_nodes
from metrics.latency import host_latency

# globals
logger = logging.getLogger(__name__)


def monitor_node_latencies():
    """Continously emits latency metric for other nodes by pinging them."""
    ID = int(os.getenv("ID"))
    nodes = get_nodes()
    other_nodes = {k: nodes[k] for k in nodes if k != ID and
                   nodes[k].hostname != "localhost"}

    if len(other_nodes) == 0:
        logger.info(f"No use to ping when running locally, aborting")
        return

    while True:
        for n_id in other_nodes:
            node = nodes[n_id]
            cmd = f"sudo sh ./metrics/ping.sh {node.hostname}".split(" ")
            res = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
            latency = float(res[0].decode().replace("\n", ""))
            host_latency.labels(ID, nodes[ID].hostname, n_id,
                                node.hostname).set(latency)
