"""Metrics related to messages."""

from prometheus_client import Gauge

host_latency = Gauge("host_latency",
                     "Latency between two nodes",
                     ["hostname", "id", "recv_id", "recv_hostname"])
