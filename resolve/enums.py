"""Enums related to the resolver and inter-module communication."""
from enum import Enum, IntEnum


class Module(Enum):
    """Represents a module."""

    VIEW_ESTABLISHMENT_MODULE = 1
    REPLICATION_MODULE = 2
    PRIMARY_MONITORING_MODULE = 3


class Function(Enum):
    """Represents an interface function in a module."""

    # View Establishment Module
    GET_VIEW = 1
    ALLOW_SERVICE = 2

    # Replication Module
    REPLICA_FLUSH = 3
    GET_PEND_REQS = 4
    REP_REQUEST_RESET = 5

    # Primary Monitoring Module


class MessageType(IntEnum):
    """Represents a message type sent between nodes."""

    DUMMY_TYPE = 1
