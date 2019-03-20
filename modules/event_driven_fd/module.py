"""Contains code related to the event-driven failure detector module."""

# standard
import logging
import time

# local
from modules.constants import K_ADMISSIBILITY_THRESHOLD as K, EVENT_FD_WAIT
from resolve.enums import MessageType

# globals
logger = logging.getLogger(__name__)


class EventDrivenFDModule:
    """This class models the event driven failure detector.

    The main loop of this module continuously broadcasts a token and waits
    for n-2f other processors to send the token back at least K times, upon
    when they are considered to be correct for this round and their IDs
    are stored along with the token used in the round in the variable
    last_correct_processors.
    """

    def __init__(self, id, resolver, n, f):
        """Initializes the module."""
        self.resolver = resolver
        self.id = id
        self.number_of_nodes = n
        self.number_of_byzantine = f

        self.token = 0
        self.counters = {n_id: 0 for n_id in range(self.number_of_nodes)
                         if n_id != self.id}
        self.last_correct_processors = {}

    def run(self, testing=False):
        """Main loop for the event-driven failure detector

        This loop contonously broadcasts a token, waits for at least n - 2f
        processors to send a token back at least K times and then increments
        the token and repeats. The last set of correct processors are stored
        along with the token used in that round.
        """
        # block until system is ready
        while not testing and not self.resolver.system_running():
            time.sleep(EVENT_FD_WAIT)

        while True:
            # broadcast token to all other nodes
            self.broadcast()
            # block until at least n-2f processors have sent K tokens back
            while not self.correct_processors_have_replied():
                time.sleep(EVENT_FD_WAIT)

            # tokens received from n-2f processors, save their IDs
            correct_ids = self.get_correct_processors()
            logger.debug(f"Nodes {correct_ids} correct for token {self.token}")
            self.last_correct_processors = {
                "token": self.token,
                "correct_processors": correct_ids
            }
            # reset all counters
            self.counters = {n_id: 0 for n_id in range(self.number_of_nodes)
                             if n_id != self.id}
            # increment token
            self.token += 1

            if testing:
                break

    def on_msg_recv(self, msg):
        """Called whenever a token is received from another processor

        If the received token is owned by this processor and it matches
        the current token, then the counter for the sending node is incremented
        before the token is sent back to the sender. If this processor owns the
        token but it does not match the current token, it is a leftover message
        from another round and no action is performed.
        """
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

    def get_correct_processors(self):
        """Returns the correct processors for this round

        A correct processor is a processor that has acked a this processor's
        current token at least K times.
        """
        return [n_id for n_id in self.counters if self.counters[n_id] >= K]

    def correct_processors_have_replied(self):
        """Returns True if >= n-2f processors have rent, i.e. acked K tokens"""
        correct_processors = self.get_correct_processors()
        return len(correct_processors) >= (self.number_of_nodes - 2 *
                                           self.number_of_byzantine)

    def send_token(self, processor_id, token, owner_id):
        """Sends a token to another processor."""
        msg = {
            "type": MessageType.EVENT_DRIVEN_FD_MESSAGE,
            "sender": self.id,
            "data": {
                "token": token,
                "owner_id": owner_id
            }
        }
        self.resolver.send_to_node(processor_id, msg, True)

    def broadcast(self):
        """Broadcasts a fresh token to all other processors

        This processor is considered to be the owner of this token.
        """
        for processor_id in range(self.number_of_nodes):
            if processor_id != self.id:
                self.send_token(processor_id, self.token, self.id)

    def get_data(self):
        """Returns current values on local variables."""
        return {
            "last_correct_processors": self.last_correct_processors,
            "current_token": self.token,
            "counters": self.counters,
            "k_threshold": K
        }
