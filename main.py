"""Main application for BFTList."""
import asyncio
import os
import conf.config as config
from communication import send, recv
from threading import Thread
from api.server import start_server
from modules.view_establishment.module import ViewEstablishmentModule
from modules.replication.module import ReplicationModule
from modules.primary_monitoring.module import PrimaryMonitoringModule
from resolve.enums import Module
from resolve.resolver import Resolver
from prometheus_client import start_http_server

id = int(os.getenv("ID", 0))


def start_api(resolver):
    """Starts BFTList API in a separate thread."""
    thread = Thread(target=start_server, args=(resolver,))
    thread.start()


def start_modules(resolver):
    """Starts all modules in separate threads."""
    n = int(os.getenv("NUMBER_OF_NODES", 0))
    f = int(os.getenv("NUMBER_OF_BYZANTINE", 0))

    if n == 0:
        print("Warning: env var NUMBER_OF_NODES not set or set to 0")
    if f == 0:
        print("Warning: env var NUMBER_OF_BYZANTINE not set or set to 0")

    modules = {
        Module.VIEW_ESTABLISHMENT_MODULE:
            ViewEstablishmentModule(id, resolver, n, f),
        Module.REPLICATION_MODULE:
            ReplicationModule(id, resolver),
        Module.PRIMARY_MONITORING_MODULE:
            PrimaryMonitoringModule(id, resolver)
    }

    # start threads and attach to resolver
    for m in modules.values():
        t = Thread(target=m.run)
        t.start()
    resolver.set_modules(modules)


def setup_communication(resolver):
    """Sets up the communication using asyncio event loop."""
    loop = asyncio.get_event_loop()
    nodes = config.get_nodes()

    # setup sender channel to other nodes
    senders = {}
    for _, node in nodes.items():
        if id != node.id:
            sender = send.Sender(node.ip, node.port)
            loop.create_task(sender.start())
            senders[node.id] = sender

    # setup receiver channel from other nodes
    receiver = recv.Receiver(nodes[id].ip, nodes[id].port, resolver)
    loop.create_task(receiver.tcp_listen())

    resolver.senders = senders
    resolver.receiver = receiver

    loop.run_forever()
    loop.close()


def setup_metrics():
    """Starts metrics server for Prometheus scraper on port 600{ID}."""
    port = 6000 + id
    start_http_server(port)
    print("Node {}: Running on {}".format(id, port))


def setup_logging():
    """Sets up logging for BFTList. TODO implement"""
    return


if __name__ == "__main__":
    resolver = Resolver()

    setup_logging()
    setup_metrics()
    start_modules(resolver)
    # start_api(resolver)
    setup_communication(resolver)
