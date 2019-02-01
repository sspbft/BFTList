"""Contains code related to the module resolver."""
from resolve.enums import Function, Module, MessageType
from conf.config import get_nodes
from communication.pack_helper import PackHelper
import json


class Resolver:
    """Module resolver that facilitates communication between modules."""

    def __init__(self):
        """Initializes the resolver."""
        self.modules = None
        self.senders = {}
        self.receiver = None
        self.nodes = get_nodes()
        self.pack_helper = PackHelper()

    def set_modules(self, modules):
        """Sets the modules dict of the resolver."""
        self.modules = modules

    def execute(self, module, func):
        """API for executing a function on a given module."""
        if self.modules is None:
            return -1

        if module == Module.VIEW_ESTABLISHMENT_MODULE:
            return self.view_establishment_exec(func)
        elif module == Module.REPLICATION_MODULE:
            return self.replication_exec(func)
        elif module == Module.PRIMARY_MONITORING_MODULE:
            return self.primary_monitoring_exec(func)
        else:
            raise ValueError("Bad module parameter")

    def view_establishment_exec(self, func):
        """Executes a function on the View Establishment module."""
        module = self.modules[Module.VIEW_ESTABLISHMENT_MODULE]
        if func == Function.GET_VIEW:
            return module.get_view()
        elif func == Function.ALLOW_SERVICE:
            return module.allow_service()
        else:
            raise ValueError("Bad function parameter")

    def replication_exec(self, func):
        """Executes a function on the Replication module."""
        raise NotImplementedError

    def primary_monitoring_exec(self, func):
        """Executes a function on the Primary Monitoring module."""
        raise NotImplementedError

    # inter-node communication methods
    def send_to(self, node_id, msg_dct):
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
            self.send_to(node_id, msg_dct)

    def dispatch_msg(self, msg, sender_id):
        """Routes received message to the correct module."""
        if msg["msg_type"] == MessageType.DUMMY_TYPE:
            self.modules[Module.VIEW_ESTABLISHMENT_MODULE].on_dummy_msg(msg)
        else:
            raise NotImplementedError
