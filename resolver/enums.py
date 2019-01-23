from enum import Enum

class Module(Enum):
    VIEW_ESTABLISHMENT_MODULE = 1
    REPLICATION_MODULE = 2
    PRIMARY_MONITORING_MODULE = 3

class Function(Enum):
    GET_VIEW = 1