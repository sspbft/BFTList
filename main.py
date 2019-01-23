from threading import Thread

from api.server import start_server
from resolver.resolver import Resolver
from modules.view_establishment.module import ViewEstablishmentModule
from modules.replication.module import ReplicationModule
from modules.primary_monitoring.module import PrimaryMonitoringModule
from resolver.enums import Module

def start_api(resolver):
    print("Starting API")
    thread = Thread(target = start_server, args=(resolver,))
    thread.start()

def start_modules(resolver):
    print("Starting modules")

    modules = {
        Module.VIEW_ESTABLISHMENT_MODULE: ViewEstablishmentModule(resolver=resolver),
        Module.REPLICATION_MODULE: ReplicationModule(resolver=resolver),
        Module.PRIMARY_MONITORING_MODULE: PrimaryMonitoringModule(resolver=resolver)
    }

    # start threads and attach to resolver
    for m in modules.values():
        t = Thread(target=m.run)
        t.start()
    resolver.set_modules(modules)

if __name__ == "__main__":
    resolver = Resolver()
    start_api(resolver=resolver)
    start_modules(resolver=resolver)