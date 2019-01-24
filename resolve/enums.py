"""Enums related to the resolver and inter-module communication."""

from enum import Enum


class Module(Enum):
    """Represents a module."""

    VIEW_ESTABLISHMENT_MODULE = 1
    REPLICATION_MODULE = 2
    PRIMARY_MONITORING_MODULE = 3


class Function(Enum):
    """Represents an interface function in a module."""

    GET_VIEW = 1
