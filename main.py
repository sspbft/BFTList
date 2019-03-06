"""Main script for BFTList."""

# standard
import asyncio
import os
import logging
from threading import Thread

# external
from prometheus_client import start_http_server

# local
from communication.sender import Sender
from communication.receiver import Receiver
import conf.config as config
from api.server import start_server
from modules.view_establishment.module import ViewEstablishmentModule
from modules.replication.module import ReplicationModule
from modules.primary_monitoring.module import PrimaryMonitoringModule
from modules.primary_monitoring.failure_detector import FailureDetectorModule
from resolve.enums import Module, SystemStatus
from resolve.resolver import Resolver

# globals
id = int(os.getenv("ID", 0))
logger = logging.getLogger(__name__)


def start_api(resolver):
    """Starts BFTList API in a separate thread."""
    thread = Thread(target=start_server, args=(resolver,))
    thread.start()


def start_modules(resolver):
    """Starts all modules in separate threads."""
    n = int(os.getenv("NUMBER_OF_NODES", 0))
    f = int(os.getenv("NUMBER_OF_BYZANTINE", 0))
    k = int(os.getenv("NUMBER_OF_CLIENTS", 0))

    if n == 0:
        logger.warning("Env var NUMBER_OF_NODES not set or set to 0")
    if f == 0:
        logger.warning("Env var NUMBER_OF_BYZANTINE not set or set to 0")
    if k == 0:
        logger.warning("Env var NUMBER_OF_CLIENTS not set or set to 0")

    modules = {
        Module.VIEW_ESTABLISHMENT_MODULE:
            ViewEstablishmentModule(id, resolver, n, f),
        Module.REPLICATION_MODULE:
            ReplicationModule(id, resolver, n, f, k),
        Module.PRIMARY_MONITORING_MODULE:
            PrimaryMonitoringModule(id, resolver, n, f),
        Module.FAILURE_DETECTOR_MODULE:
            FailureDetectorModule(id, resolver, n, f)
    }

    resolver.set_modules(modules)

    # start threads and attach to resolver
    for m in modules.values():
        t = Thread(target=m.run)
        t.start()


def setup_communication(resolver):
    """Sets up the communication using asyncio event loop."""
    nodes = config.get_nodes()

    # setup receiver to receiver channel messages from other nodes
    receiver = Receiver(id, nodes[id].ip, nodes[id].port, resolver)
    t = Thread(target=receiver.start)
    t.start()

    # setup sender channel to other nodes
    senders = {}
    for _, node in nodes.items():
        if id != node.id:
            sender = Sender(id, node)
            senders[node.id] = sender
    logger.info("All senders connected")

    resolver.senders = senders
    resolver.receiver = receiver

    loop = asyncio.get_event_loop()
    for i in senders:
        loop.create_task(senders[i].start())

    resolver.system_status = SystemStatus.READY

    loop.run_forever()
    loop.close()


def setup_metrics():
    """Starts metrics server for Prometheus scraper on port 600{ID}."""
    try:
        port = 6000 + id
        start_http_server(port, addr="0.0.0.0")
        logger.info(f"Metrics server setup on port {port}")
    except Exception as e:
        logger.error(f"Could not setup metrics. Got error: {e}")


def setup_logging():
    """Sets up logging for BFTList."""
    colors = ["\033[95m", "\033[94m", "\033[92m", "\033[93m",
              "\033[91m", "\033[0m"]
    node_color = colors[id % len(colors)]
    end_color = colors[len(colors) - 1]

    FORMAT = f"{node_color}BFTList.%(name)s : Node {id}" + " ==> " + \
             "[%(levelname)s] : %(message)s" + f"{end_color}"
    level = logging.NOTSET if os.getenv("DEBUG") is not None else logging.INFO
    logging.basicConfig(format=FORMAT, level=level)

    # only log ERROR messages from external loggers
    externals = ["werkzeug", "asyncio, engineio", "engineio.client",
                 "engineio.server", "socketio.client", "socketio.server",
                 "urllib3.connectionpool"]
    for e in externals:
        logging.getLogger(e).setLevel(logging.ERROR)

    logger.info("Logging configured")


if __name__ == "__main__":
    resolver = Resolver()

    setup_logging()
    if os.getenv("BYZANTINE"):
        logger.warning("Node is acting Byzantine: " +
                       f"{os.getenv('BYZANTINE_BEHAVIOR')}")
    setup_metrics()
    start_modules(resolver)
    start_api(resolver)
    setup_communication(resolver)
