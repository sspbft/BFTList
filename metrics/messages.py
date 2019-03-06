"""Metrics related to messages."""

from prometheus_client import Counter, Gauge

msgs_sent = Counter("msg_sent",
                    "Number of messages sent between nodes",
                    ["node_id"])

msg_rtt = Gauge("msg_rtt",
                "Time taken to send a message to a node and get an ACK",
                ["node_id", "receiver_id"])
