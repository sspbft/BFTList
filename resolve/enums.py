"""Enums related to the resolver and inter-module communication."""
from enum import Enum, IntEnum


class Module(Enum):
    """Represents a module."""

    VIEW_ESTABLISHMENT_MODULE = 1
    REPLICATION_MODULE = 2
    PRIMARY_MONITORING_MODULE = 3
    FAILURE_DETECTOR_MODULE = 4


class Function(Enum):
    """Represents an interface function in a module."""

    # View Establishment Module
    GET_CURRENT_VIEW = 1  # re-named from getView in the paper
    ALLOW_SERVICE = 2
    VIEW_CHANGE = 3

    # Replication Module
    REPLICA_FLUSH = 4
    GET_PEND_REQS = 5
    REP_REQUEST_RESET = 6

    # Primary Monitoring Module
    NO_VIEW_CHANGE = 7

    # Failure detector module
    SUSPECTED = 8


class MessageType(IntEnum):
    """Represents a message type sent between nodes."""

    VIEW_ESTABLISHMENT_MESSAGE = 1
    REPLICATION_MESSAGE = 2
    PRIMARY_MONITORING_MESSAGE = 3
    FAILURE_DETECTOR_MESSAGE = 4
