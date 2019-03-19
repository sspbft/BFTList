"""Contains code related to the module resolver."""

# standard
import logging
from threading import Lock, Thread
import os
import requests
import time

# local
import modules.byzantine as byz
from resolve.enums import Function, Module, MessageType, SystemStatus
from conf.config import get_nodes
from modules.replication.models.client_request import ClientRequest
from communication.zeromq import rate_limiter
from metrics.messages import msg_rtt, msg_sent_size, msgs_sent, bytes_sent

# globals
logger = logging.getLogger(__name__)


class Resolver:
    """Module resolver that facilitates communication between modules."""

    def __init__(self, testing=False):
        """Initializes the resolver."""
        self.modules = None
        self.senders = {}
        self.fd_senders = {}
        self.receiver = None
        self.fd_receiver = None
        self.nodes = get_nodes()

        # locks used to avoid race conditions with modules
        self.view_est_lock = Lock()
        self.replication_lock = Lock()
        self.prim_mon_lock = Lock()

        self.own_comm_ready = False
        self.other_comm_ready = False
        self.system_status = SystemStatus.BOOTING

        # check other nodes for system ready before starting system
        if not testing:
            t = Thread(target=self.wait_for_other_nodes)
            t.start()

        # inject resolver in rate limiter module
        rate_limiter.resolver = self

    def wait_for_other_nodes(self):
        """Write me."""
        if len(self.nodes) == 1:
            self.other_comm_ready = True
            return

        system_ready = False
        while not system_ready:
            nodes_ready = []
            for n_id, node in self.nodes.items():
                try:
                    r = requests.get(f"http://{node.hostname}:{4000 + n_id}")
                    is_ready = (r.status_code == 200 and
                                r.json()["status"] !=
                                SystemStatus.BOOTING.name)
                    nodes_ready.append(is_ready)
                except Exception:
                    nodes_ready.append(False)
            system_ready = all(nodes_ready)
            if not system_ready:
                time.sleep(0.1)
        self.system_status = SystemStatus.RUNNING
        logger.info(f"System running at UNIX time {time.time()}")

    def system_running(self):
        """Return True if the system as a whole i running."""
        return self.system_status == SystemStatus.RUNNING

    def set_modules(self, modules):
        """Sets the modules dict of the resolver."""
        self.modules = modules

    def execute(self, module, func, *args):
        """API for executing a function on a given module."""
        if module == Module.VIEW_ESTABLISHMENT_MODULE:
            return self.view_establishment_exec(func, *args)
        elif module == Module.REPLICATION_MODULE:
            return self.replication_exec(func, *args)
        elif module == Module.PRIMARY_MONITORING_MODULE:
            return self.primary_monitoring_exec(func, *args)
        elif module == Module.FAILURE_DETECTOR_MODULE:
            return self.failure_detector_exec(func, *args)
        else:
            raise ValueError("Bad module parameter")

    def view_establishment_exec(self, func, *args):
        """Executes a function on the View Establishment module."""
        module = self.modules[Module.VIEW_ESTABLISHMENT_MODULE]
        if func == Function.GET_CURRENT_VIEW:
            if os.getenv("FORCE_VIEW"):
                return int(os.getenv("FORCE_VIEW"))
            return module.get_current_view(args[0])
        elif func == Function.ALLOW_SERVICE:
            if os.getenv("ALLOW_SERVICE"):
                return True
            return module.allow_service()
        elif func == Function.VIEW_CHANGE:
            return module.view_change()
        else:
            raise ValueError("Bad function parameter")

    def replication_exec(self, func):
        """Executes a function on the Replication module."""
        module = self.modules[Module.REPLICATION_MODULE]
        if func == Function.GET_PEND_REQS:
            return module.get_pend_reqs()
        elif func == Function.REP_REQUEST_RESET:
            return module.rep_request_reset()
        elif func == Function.REPLICA_FLUSH:
            return module.replica_flush()
        elif func == Function.NEED_FLUSH:
            return module.rep_need_flush()
        else:
            raise ValueError("Bad function parameter")

    def primary_monitoring_exec(self, func):
        """Executes a function on the Primary Monitoring module."""
        if func == Function.NO_VIEW_CHANGE:
            if os.getenv("FORCE_NEW_VIEW_CHANGE"):
                return True
            return True
        else:
            raise ValueError("Bad function parameter")

    def failure_detector_exec(self, func):
        """Executes a function on the Failure Detector module."""
        module = self.modules[Module.FAILURE_DETECTOR_MODULE]
        if func == Function.SUSPECTED:
            return module.suspected()
        else:
            raise ValueError("Bad function parameter")

    # inter-node communication methods
    def send_to_node(self, node_id, msg_dct, fd_msg=False):
        """Sends a message to a given node.

        Message should be a dictionary, which will be serialized to json
        and converted to a byte object before sent over the links to
        the other node.
        """
        if node_id not in self.senders and node_id not in self.fd_senders:
            logger.error(f"Non-existing sender for node {node_id}")

        if byz.is_byzantine():
            # don't send messages if Byzantine and UNRESPONSIVE
            if byz.get_byz_behavior() == byz.UNRESPONSIVE:
                return
            # Only send message to half of the nodes if Byzantine and
            # UNRESPONSIVE_TO_SOME
            if (byz.get_byz_behavior() == byz.UNRESPONSIVE_TO_HALF and
               (node_id % 2 != 0)):
                return

        try:
            sender = (self.senders[node_id] if not fd_msg else
                      self.fd_senders[node_id])
            sender.add_msg_to_queue(msg_dct)
        except Exception as e:
            logger.error(f"Something went wrong when sending msg {msg_dct} " +
                         f"to node {node_id}. Error: {e}")

    def broadcast(self, msg_dct):
        """Broadcasts a message to all nodes."""
        for node_id, _ in self.senders.items():
            self.send_to_node(node_id, msg_dct)

    def dispatch_msg(self, msg):
        """Routes received message to the correct module."""
        msg_type = msg["type"]
        if msg_type == MessageType.VIEW_ESTABLISHMENT_MESSAGE:
            try:
                self.view_est_lock.acquire()
                self.modules[Module.VIEW_ESTABLISHMENT_MODULE].receive_msg(msg)
            finally:
                self.view_est_lock.release()
        elif msg_type == MessageType.REPLICATION_MESSAGE:
            try:
                self.replication_lock.acquire()
                self.modules[Module.REPLICATION_MODULE].receive_rep_msg(msg)
            finally:
                self.replication_lock.release()
        elif msg_type == MessageType.PRIMARY_MONITORING_MESSAGE:
            try:
                self.prim_mon_lock.acquire()
                self.modules[Module.PRIMARY_MONITORING_MODULE].receive_msg(msg)
            finally:
                self.prim_mon_lock.release()
        elif msg_type == MessageType.FAILURE_DETECTOR_MESSAGE:
            self.modules[Module.FAILURE_DETECTOR_MODULE].receive_msg(msg)
        elif msg_type == MessageType.EVENT_DRIVEN_FD_MESSAGE:
            self.modules[Module.EVENT_DRIVEN_FD_MODULE].on_msg_recv(msg)
        else:
            logger.warning(f"Message with invalid type {msg_type} cannot be" +
                           " dispatched")

    def on_message_sent(self, msg={}, metric_data={}):
        """Callback function when a communication module has sent the message.

        Used for metrics purpose.
        """
        id = int(os.getenv("ID"))
        # emit message sent message
        msgs_sent.labels(id).inc()

        # Emit roundtrip time for message
        if ("rec_id" in metric_data and "recv_hostname" in metric_data and
           "latency" in metric_data):
            msg_rtt.labels(id,
                           metric_data["rec_id"],
                           metric_data["recv_hostname"]).set(
                                metric_data["latency"])
        # Emit size of sent message
        if ("msg_type" in metric_data and "bytes_size" in metric_data):
            bytes_sent.labels(id,
                              metric_data["msg_type"]).inc(
                                  metric_data["bytes_size"])
            if("type" in msg):
                msg_sent_size.labels(
                                id,
                                msg["type"],
                                metric_data["msg_type"]).set(
                                    metric_data["bytes_size"])

    # Methods to extract data
    def get_view_establishment_data(self):
        """Returns current values of variables.

        View Establishment module.
        """
        return self.modules[Module.VIEW_ESTABLISHMENT_MODULE].get_data()

    def get_replication_data(self):
        """Returns current values of variables.

        Replication module.
        """
        return self.modules[Module.REPLICATION_MODULE].get_data()

    def get_primary_monitoring_data(self):
        """Returns current values of variables.

        Primary Monitoring module.
        """
        prim_mon = self.modules[Module.PRIMARY_MONITORING_MODULE].get_data()
        fail_det = self.modules[Module.FAILURE_DETECTOR_MODULE].get_data()
        return {**prim_mon, **fail_det}

    def get_failure_detector_data(self):
        """Returns current values of variables.

        Failure detector module.
        """
        return self.modules[Module.FAILURE_DETECTOR_MODULE].get_data()

    def get_event_driven_fd_data(self):
        """Returns current values of variables.

        Event-driven failure detector module.
        """
        return self.modules[Module.EVENT_DRIVEN_FD_MODULE].get_data()

    def inject_client_req(self, req: ClientRequest):
        """Injects a ClientRequest sent from a client through the API."""
        return self.modules[Module.REPLICATION_MODULE].inject_client_req(req)
