"""Self-stabilizing asynchronous sender channel."""

# standard
import logging
import zmq
import jsonpickle
import time

# local
from metrics.messages import msgs_sent
from .message import Message, MessageEnum

# globals
logger = logging.getLogger(__name__)


class Receiver():
    """Models a self-stabilizing receiver channel.

    The receiver sets up an async socketio server that clients (Senders) can
    connect to in order to send messages.
    """

    def __init__(self, id, ip, port, resolver):
        """Initializes the sender."""
        self.id = id
        self.ip = ip
        self.port = port
        self.resolver = resolver

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")

        self.msgs_received = 0

    def start(self):
        """Starts the zeromq server."""
        while True:
            msg_bytes = self.socket.recv()
            msg_json = msg_bytes.decode()
            msg = jsonpickle.decode(msg_json)
            logger.info(f"Got msg from node {msg.get_sender_id()}")
            self.resolver.dispatch_msg(msg.get_data())
            self.ack(msg.get_counter())

    def ack(self, counter):
        """Sends a message over the specified channel."""
        msgs_sent.labels(self.id).inc(1)
        if self.msgs_received == 0:
            self.start_time = time.time()
        self.msgs_received += 1
        msg = Message(MessageEnum.RECEIVER_MESSAGE, counter, self.id)
        self.socket.send(msg.as_bytes())
