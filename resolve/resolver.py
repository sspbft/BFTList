"""Contains code related to the module resolver."""
from resolve.enums import Function, Module, MessageType
from conf.config import get_nodes
from communication.pack_helper import PackHelper
import json
from threading import Lock


class Resolver:
    """Module resolver that facilitates communication between modules."""

    def __init__(self):
        """Initializes the resolver."""
        self.modules = None
        self.senders = {}
        self.receiver = None
        self.pack_helper = PackHelper()
        self.nodes = get_nodes()
        self.lock = Lock()

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
            msg_json = json.dumps(msg_dct)
            byte_obj = self.pack_helper.pack(msg_json.encode())
            self.senders[node_id].add_msg_to_queue(byte_obj)

    def broadcast(self, msg_dct):
        """Broadcasts a message to all nodes."""
        for node_id, _ in self.senders.items():
            self.send_to_node(node_id, msg_dct)

    def dispatch_msg(self, msg, sender_id):
        """Routes received message to the correct module."""
        self.lock.acquire()
        try:
            msg_type = msg["type"]
            if msg_type == MessageType.VIEW_ESTABLISHMENT_MESSAGE:
                self.modules[Module.VIEW_ESTABLISHMENT_MODULE].receive_msg(msg)
            elif msg_type == MessageType.REPLICATION_MESSAGE:
                self.modules[Module.REPLICATION_MODULE].receive_rep_msg(msg)
            else:
                raise NotImplementedError
        finally:
            self.lock.release()

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
