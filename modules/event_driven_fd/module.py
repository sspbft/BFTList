"""TODO write me"""

# standard
import logging
import time

# local
from modules.constants import K_ADMISSIBILITY_THRESHOLD as K, EVENT_FD_WAIT
from resolve.enums import MessageType

# globals
logger = logging.getLogger(__name__)


class EventDrivenFDModule:
    """TODO write me."""

    def __init__(self, id, resolver, n, f):
        """Initializes the module."""
        self.resolver = resolver
        self.id = id
        self.number_of_nodes = n
        self.number_of_byzantine = f

        self.token = 0
        self.counters = {n_id: 0 for n_id in range(self.number_of_nodes)}
        self.last_correct_processors = []

    def run(self, testing=False):
        """TODO write me."""
        # block until system is ready
        while not testing and not self.resolver.system_running():
            time.sleep(0.1)

        while True:
            # broadcast token to all other nodes
            self.broadcast()
            # block until at least n-2f processors have sent K tokens back
            while not self.correct_processors_have_replied():
                time.sleep(EVENT_FD_WAIT)

            # tokens received from n-2f processors, save their IDs
            correct_processors = self.correct_processors()
            self.last_correct_processors = {
                "token": self.token,
                "correct_processors": correct_processors
            }
            # reset all counters
            self.counters = {n_id: 0 for n_id in range(self.number_of_nodes)}
            # increment token
            self.token += 1

    def on_msg_recv(self, msg):
        """TODO write me."""
        # increment counter for node if current token is returned
        sender_id = msg["sender"]
        token = msg["data"]["token"]
        owner_id = msg["data"]["owner_id"]

        # increment counter for sender if own, correct token is returned
        if owner_id == self.id:
            if token == self.token:
                self.counters[sender_id] += 1
            else:
                # if invalid token, break out of token exchange loop
                return

        # send back token to sender
        self.send_token(sender_id, token, owner_id)

    def correct_processors(self):
        """TODO write me."""
        return [n_id for n_id in self.counters if self.counters[n_id] >= K]

    def correct_processors_have_replied(self):
        """TODO write me."""
        correct_processors = self.get_correct_processors()
        return len(correct_processors) >= (self.number_of_nodes - 2 *
                                           self.number_of_byzantine)

    def send_token(self, node_id, token, owner_id):
        """TODO write me."""
        msg = {
            "type": MessageType.EVENT_DRIVEN_FD_MESSAGE,
            "sender": self.id,
            "data": {
                "token": token,
                "owner_id": owner_id
            }
        }
        self.resolver.send_to_node(node_id, msg, fd_msg=True)

    def broadcast(self):
        """TODO write me."""
        for node_id in range(self.number_of_nodes):
            self.send_token(self.token, node_id, self.id)
