"""Main application for BFTList."""
import asyncio
import os
import conf.config as config
from communication import send, recv
from threading import Thread
from api.server import start_server
from resolve.resolver import Resolver
from modules.view_establishment.module import ViewEstablishmentModule
from modules.replication.module import ReplicationModule
from modules.primary_monitoring.module import PrimaryMonitoringModule
from resolve.enums import Module


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
    _self = list(filter(lambda n: n.id == id, nodes))[0]

    # setup sender channel to other nodes
    for node in config.get_nodes():
        if id != node.id:
            sender = send.Sender(ip=node.ip, port=node.port)
            loop.create_task(sender.start())

    # setup receiver channel from other nodes
    receiver = recv.Receiver(_self.ip, _self.port)
    loop.create_task(receiver.tcp_listen())

    loop.run_forever()
    loop.close()


if __name__ == "__main__":
    resolver = Resolver()
    # start_api(resolver=resolver)
    # start_modules(resolver=resolver)
    setup_communication()
