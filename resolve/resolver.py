"""Contains code related to the module resolver."""

# standard
import jsonpickle
import logging
from threading import Lock

# local
from resolve.enums import Function, Module, MessageType
from conf.config import get_nodes
from communication.pack_helper import PackHelper

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

    def set_modules(self, modules):
        """Sets the modules dict of the resolver."""
        self.modules = modules

    def execute(self, module, func, *args):
        """API for executing a function on a given module."""
        if self.modules is None:
            return -1

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
            return module.get_current_view(args[0])
        elif func == Function.ALLOW_SERVICE:
            return module.allow_service()
        elif func == Function.VIEW_CHANGE:
            return module.view_change()
        else:
            raise ValueError("Bad function parameter")

    def replication_exec(self, func):
        """Executes a function on the Replication module."""
        pass
        # raise NotImplementedError

    def primary_monitoring_exec(self, func):
        """Executes a function on the Primary Monitoring module."""
        raise NotImplementedError

    # inter-node communication methods
    def send_to_node(self, node_id, msg_dct):
        """Sends a message to a given node.

        Message should be a dictionary, which will be serialized to json
        and converted to a byte object before sent over the links to
        the other node.
        """
        if node_id in self.senders:
            msg_json = jsonpickle.encode(msg_dct)
            byte_obj = self.pack_helper.pack(msg_json.encode())
            self.senders[node_id].add_msg_to_queue(byte_obj)

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
