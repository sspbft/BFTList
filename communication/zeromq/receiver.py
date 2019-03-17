"""Asynchronous receiver channel."""

# standard
import logging
import zmq
import jsonpickle
import time

# local
from .message import Message, MessageEnum

# globals
logger = logging.getLogger(__name__)


class Receiver():
    """Models a receiver channel for the zeromq/TCP protocol.

    The receiver sets up a zeromq server that clients (Senders) can
    connect to in order to send messages.
    """

    def __init__(self, id, ip, port, resolver, on_ack=None):
        """Initializes the receiver."""
        self.id = id
        self.ip = ip
        self.port = port
        self.resolver = resolver
        self.on_ack = on_ack

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        logger.info(f"Receiver channel setup on port {self.port}")

        self.msgs_received = 0

    def start(self):
        """Starts the zeromq server."""
        while True:
            msg_bytes = self.socket.recv()
            msg_json = msg_bytes.decode()
            msg = jsonpickle.decode(msg_json)
            self.resolver.dispatch_msg(msg.get_data())
            self.ack(msg.get_counter())

    def ack(self, counter):
        """Sends a message over the specified channel."""
        if self.msgs_received == 0:
            self.start_time = time.time()
        self.msgs_received += 1
        msg = Message(MessageEnum.RECEIVER_MESSAGE, counter, self.id)
        if self.on_ack is not None:
            self.on_ack()
        self.socket.send(msg.as_bytes())
