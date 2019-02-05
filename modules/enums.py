"""Enums related to the modules of the algorithm."""
from enum import Enum


class PrimaryMonitoringEnums(Enum):
    """Represents a string for v_status."""

    OK = 1
    NO_SERVICE = 2
    V_CHANGE = 3


class ViewEstablishmentEnums(Enum):
    """Represents strings for return values from automaton."""

    NO_ACTION = 1
    RESET = 2
    NO_RETURN_VALUE = 3

    PREDICATE = 4
    ACTION = 5


class ReplicationEnums(Enum):
    """Represent status for messages."""

    PRE_PREP = 0
    PREP = 1
    COMMIT = 2
