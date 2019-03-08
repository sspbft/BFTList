"""Metrics related to messages."""

from prometheus_client import Counter, Gauge, Summary

msgs_sent = Counter("msg_sent",
                    "Number of messages sent between nodes",
                    ["node_id"])

# NOTE will probable be removed later in favor of msg_latency
msg_rtt = Gauge("msg_rtt",
                "Time taken to send a message to a node and get an ACK",
                ["node_id", "receiver_id", "receiver_hostname"])

msg_latency = Summary("msg_latency",
                      "Time between sending a message and getting ACK",
                      "node_id", "receiver_id", "receiver_hostname"
                      )

msgs_in_queue = Gauge("msgs_in_queue",
                      "The amount of messages waiting to be sent over channel",
                      ["node_id", "receiver_id", "receiver_hostname"])
