"""Metrics related to messages."""

from prometheus_client import Counter, Gauge

msgs_sent = Counter("msg_sent",
                    "Number of messages sent between nodes",
                    ["node_id"])

msg_rtt = Gauge("msg_rtt",
                "Time taken to send a message to a node and get an ACK",
                ["node_id", "receiver_id", "receiver_hostname"])

msgs_in_queue = Gauge("msgs_in_queue",
                      "The amount of messages waiting to be sent over channel",
                      ["node_id", "receiver_id", "receiver_hostname"])

view_change = Counter("view_change",
                      "Number of times there has been a view change",
                      ["node_id"])

allow_service_rtt = Gauge("allow_service_rtt",
                          "Time taken from declining service to allowing",
                          ["node_id", "view_from"])
