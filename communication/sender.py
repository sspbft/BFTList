"""Self-stabilizing asynchronous sender channel."""

# standard
import asyncio
import logging
import socketio
from queue import Queue
import jsonpickle

# local
from metrics.messages import msgs_sent
from .message import Message, MessageEnum

# globals
logger = logging.getLogger(__name__)


class Sender():
    """Models a self-stabilizing sender channel.

    The sender connects to the running socket server on the receiving node in
    order to send messages over the specified channel.
    """

    def __init__(self, id, recv_id, recv_ip, recv_port):
        """Initializes the sender."""
        self.id = id
        self.recv_id = recv_id
        self.recv_ip = recv_ip
        self.recv_port = recv_port

        self.sio = socketio.Client()
        self.msg_queue = Queue()
        self.counter = 1
        self.cap = 2**31

    def add_msg_to_queue(self, msg):
        """Adds the message to the FIFO queue for this sender channel."""
        self.msg_queue.put(msg)

    def get_msg_from_queue(self):
        """Gets the next message from the queue.

        Will block until there is a message to send.
        """
        if self.msg_queue.empty():
            return None
        msg = self.msg_queue.get()
        return msg

    def on_message(self, msg):
        """Called when a message is received from the server."""
        msg = jsonpickle.decode(msg)

    def on_connect(self):
        """Called when connected to the server (Receiver)."""
        # logger.info(f"Connected to {self.recv_ip}:{self.recv_port}")
        logger.info(f"Connected to {self.recv_id}")

    def on_disconnect(self):
        """Called when disconnected from the server (Receiver)."""
        logger.info(f"Disconnected from {self.recv_ip}:{self.recv_port}")

    async def start(self):
        """Main loop for the sender channel."""
        # set up handlers
        self.sio.on("message", handler=self.on_message)
        self.sio.on("connect", handler=self.on_connect)
        self.sio.on("disconnect", handler=self.on_disconnect)

        logger.info(f"{self.id}_{self.recv_id} set up")

        while True:
            msg = self.get_msg_from_queue()
            if msg is None:
                await asyncio.sleep(0.1)
            else:
                await self.send(msg)
                self.counter += 1 % self.cap

    async def send(self, data):
        """Sends a message over the specified channel.

        Constructs a message consisting of the token and the payload and sends
        it over the socket.
        """
        msgs_sent.labels(self.id).inc()
        await asyncio.sleep(0.1)
        print(data)
        # msg_json = jsonpickle.encode(msg)
        msg = Message(MessageEnum.SENDER_MESSAGE, self.counter, self.id, data)
        # logger.info(f"sending msg to {self.recv_id}")
        self.sio.send(msg.as_json())

    async def connect(self):
        """Blocking func that connects the client to the specified server."""
        while self.sio.eio.state != "connected":
            logger.debug(f"trying to connect to http://{self.recv_ip}:{self.recv_port}")
            try:
                self.sio.connect(f"http://{self.recv_ip}:{self.recv_port}")
            except socketio.exceptions.ConnectionError:
                logger.error("Connection denied")
            # await asyncio.sleep(1)
        logger.info(f"Connection established {self.id}_{self.recv_id}")
