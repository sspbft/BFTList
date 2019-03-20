"""Metrics related to state and requests."""

from prometheus_client import Counter, Gauge

state_length = Counter("state_length",
                       "Length of the RSM state")
