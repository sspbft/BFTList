"""Enums related to the modules of the algorithm."""
from enum import Enum, IntEnum


class PrimaryMonitoringEnums(Enum):
    """Represents a string for v_status."""

    OK = 1
    NO_SERVICE = 2
    V_CHANGE = 3


class ViewEstablishmentEnums(IntEnum):
    """Represents strings for return values from automaton."""

    TEE = -1
    DF_VIEW = 0

    NO_ACTION = 1
    RESET = 2
    NO_RETURN_VALUE = 3

    PREDICATE = 4
    ACTION = 5

    FOLLOW = 8
    REMAIN = 9
