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


def start_api(resolver):
    """Starts BFTList API in a separate thread."""
    thread = Thread(target=start_server, args=(resolver,))
    thread.start()


def start_modules(resolver):
    """Starts all modules in separate threads."""
    modules = {
        Module.VIEW_ESTABLISHMENT_MODULE:
            ViewEstablishmentModule(resolver=resolver),
        Module.REPLICATION_MODULE:
            ReplicationModule(resolver=resolver),
        Module.PRIMARY_MONITORING_MODULE:
            PrimaryMonitoringModule(resolver=resolver)
    }

    # start threads and attach to resolver
    for m in modules.values():
        t = Thread(target=m.run)
        t.start()
    resolver.set_modules(modules)


def setup_communication():
    """Sets up the communication using asyncio event loop."""
    loop = asyncio.get_event_loop()
    nodes = config.get_nodes()
    id = int(os.getenv("ID", 0))

    # setup sender channel to other nodes
    for _, node in nodes.items():
        if id != node.id:
            sender = send.Sender(ip=node.ip, port=node.port)
            loop.create_task(sender.start())

    # setup receiver channel from other nodes
    receiver = recv.Receiver(nodes[id].ip, nodes[id].port)
    loop.create_task(receiver.tcp_listen())

    loop.run_forever()
    loop.close()


def setup_metrics():
    """Starts metrics server for Prometheus scraper on port 600{ID}."""
    id = int(os.getenv("ID", 0))
    port = 6000 + id
    start_http_server(port)
    print("Node {}: Running on {}".format(id, port))


def setup_logging():
    """Sets up logging for BFTList. TODO implement"""
    return


if __name__ == "__main__":
    setup_logging()
    setup_metrics()
    setup_communication()

    resolver = Resolver()
    start_api(resolver=resolver)
    # start_modules(resolver=resolver)
