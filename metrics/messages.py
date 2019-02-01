"""Metrics related to messages."""

from prometheus_client import Counter

msgs_sent = Counter("msg_sent",
                    "Number of messages sent between nodes",
                    ["node_id"])
