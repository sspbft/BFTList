"""Self-stabilizing asynchronous sender channel."""

# standard
import asyncio
import logging
import zmq
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

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{self.recv_ip}:{self.recv_port}")

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

    async def start(self):
        """Main loop for the sender channel."""

        while True:
            msg = self.get_msg_from_queue()
            if msg is None:
                await asyncio.sleep(0.1)
            else:
                reply = await self.send(msg)
                if reply.get_counter() != self.counter:
                    raise ValueError("did not get same counter back")
                self.counter += 1 % self.cap

    async def send(self, data):
        """Sends a message over the specified channel.

        Constructs a message consisting of the token and the payload and sends
        it over the socket.
        """
        msgs_sent.labels(self.id).inc()
        # await asyncio.sleep(0.1)
        msg = Message(MessageEnum.SENDER_MESSAGE, self.counter, self.id, data)
        self.socket.send(msg.as_bytes())
        reply_bytes = self.socket.recv()
        try:
            reply_json = reply_bytes.decode()
            reply = jsonpickle.decode(reply_json)
            return reply
        except Exception as e:
            logger.error(f"error when decoding: {e}")
            return None
