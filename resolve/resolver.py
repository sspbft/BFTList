"""Contains code related to the module resolver."""

# standard
import jsonpickle
import logging
from threading import Lock
import os

# local
from resolve.enums import Function, Module, MessageType
from conf.config import get_nodes
from communication.pack_helper import PackHelper
from modules.replication.models.client_request import ClientRequest

# globals
logger = logging.getLogger(__name__)


class Resolver:
    """Module resolver that facilitates communication between modules."""

    def __init__(self):
        """Initializes the resolver."""
        self.modules = None
        self.senders = {}
        self.receiver = None
        self.pack_helper = PackHelper()
        self.nodes = get_nodes()

        # locks used to avoid race conditions with modules
        self.view_est_lock = Lock()
        self.replication_lock = Lock()

    def is_ready(self):
        """Check function to determine if system is ready."""
        return self.modules is not None

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
        pass

    def primary_monitoring_exec(self, func):
        """Executes a function on the Primary Monitoring module."""
        if func == Function.NO_VIEW_CHANGE:
            if os.getenv("FORCE_NEW_VIEW_CHANGE"):
                return True
            return True
        else:
            raise ValueError("Bad function parameter")

    # inter-node communication methods
    def send_to_node(self, node_id, msg_dct):
        """Sends a message to a given node.

        Message should be a dictionary, which will be serialized to json
        and converted to a byte object before sent over the links to
        the other node.
        """
        if node_id in self.senders:
            self.senders[node_id].add_msg_to_queue(msg_dct)
        else:
            pass
            # logger.error(f"Non-existing sender for node {node_id}")

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
        else:
            logger.warning(f"Message with invalid type {msg_type} cannot be" +
                           "dispatched")

    # Methods to extract data
    def get_view_establishment_data(self):
        """Returns current values of variables.

        View Establishment module.
        """
        return self.modules[Module.VIEW_ESTABLISHMENT_MODULE].get_data()

    def get_replication_data(self):
        """Returns current values of variables.

        View Establishment module.
        """
        return self.modules[Module.REPLICATION_MODULE].get_data()

    def get_primary_monitoring_data(self):
        """Returns current values of variables.

        View Establishment module.
        """
        return self.modules[Module.PRIMARY_MONITORING_MODULE].get_data()

    def inject_client_req(self, req: ClientRequest):
        """Injects a ClientRequest sent from a client through the API."""
        return self.modules[Module.REPLICATION_MODULE].inject_client_req(req)
