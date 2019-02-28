"""Self-stabilizing asynchronous sender channel."""

# standard
import logging
import socketio
import eventlet
from queue import Queue
import jsonpickle

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

        self.msg_queue = Queue()
        self.clients = 0
        self.sio = socketio.Server()
        self.app = socketio.WSGIApp(self.sio)

    def add_msg_to_queue(self, msg):
        """Adds the message to the FIFO queue for this sender channel."""
        self.msg_queue.put(msg)

    async def get_msg_from_queue(self):
        """Gets the next message from the queue.

        Will block until there is a message to send.
        """
        while self.msg_queue.empty():
            continue
        msg = self.msg_queue.get()
        return msg

    def on_connect(self, sid, environ):
        """TODO write me."""
        self.clients += 1
        logger.info(f"Node {sid} connected, {self.clients} connected clients")
        pass

    def on_message(self, sid, msg):
        """TODO write me."""
        msg = jsonpickle.decode(msg)
        logger.info(f"got msg from node {msg.get_sender_id()}")
        self.resolver.dispatch_msg(msg.get_data())

    def on_disconnect(self, sid):
        """TODO write me."""
        self.clients -= 1
        logger.info(f"Node {sid} disconnected, {self.clients} connected " +
                    "clients")

    def start(self):
        """Starts the socketio server."""
        logger.info(f"Running socketio server on {self.ip}:{self.port}")
        self.sio.on("connect", self.on_connect)
        self.sio.on("message", self.on_message)
        self.sio.on("disconnect", self.on_disconnect)

        logger.info("Receiver configured and set up")
        eventlet.wsgi.server(eventlet.listen(('', self.port)), self.app,
                             log_output=False)

    def ack(self, counter, data={}):
        """Sends a message over the specified channel."""
        msgs_sent.labels(self.id).inc(1)
        msg = Message(MessageEnum.RECEIVER_MESSAGE, counter, self.id, data)
        self.sio.send(msg.as_json())
