"""Metrics related to messages."""

from prometheus_client import Counter, Gauge

msgs_sent = Counter("msg_sent",
                    "Number of messages sent between nodes",
                    ["node_id", "msg_type"])

msg_rtt = Gauge("msg_rtt",
                "Time taken to send a message to a node and get an ACK",
                ["node_id", "receiver_id", "receiver_hostname"])

msgs_in_queue = Gauge("msgs_in_queue",
                      "The amount of messages waiting to be sent over channel",
                      ["node_id", "receiver_id", "receiver_hostname"])

allow_service_rtt = Gauge("allow_service_rtt",
                          "Time taken from declining service to allowing",
                          ["node_id", "view_from"])

msg_sent_size = Gauge("msg_sent_size",
                      "Size of a message sent from node over com_mod of type \
                      msg_type",
                      ["node_id", "msg_type", "com_mod"])

bytes_sent = Counter("bytes_sent",
                     "Number of bytes sent from node over com_mod",
                     ["node_id", "com_mod"])

run_method_time = Gauge("run_method_time",
                        "Time taken to run the run-forever-loop",
                        ["node_id", "module"])

msgs_during_exp = Gauge("msgs_during_exp",
                        "Number of messages sent during an experiment",
                        ["node_id", "exp_param", "view_est_msgs",
                         "rep_msgs", "prim_mon_msgs", "fd_msgs"])

bytes_during_exp = Gauge("bytes_during_exp",
                         "Number of bytes sent during an experiment",
                         ["node_id", "exp_param"])
