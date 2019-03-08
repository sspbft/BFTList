"""Self-stabilizing asynchronous sender channel."""

# standard
import asyncio
import logging
import zmq
import time
import zmq.asyncio
from queue import Queue
import jsonpickle

# local
from metrics.messages import msgs_sent, msg_rtt, msgs_in_queue
from .message import Message, MessageEnum

# globals
logger = logging.getLogger(__name__)


class Sender():
    """Models a self-stabilizing sender channel.

    The sender connects to the running socket server on the receiving node in
    order to send messages over the specified channel.
    """

    def __init__(self, id, node):
        """Initializes the sender."""
        self.id = id
        self.recv = node

        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{self.recv.hostname}:{self.recv.port}")

        self.msg_queue = Queue()
        self.counter = 1
        self.cap = 2**31

    def add_msg_to_queue(self, msg):
        """Adds the message to the FIFO queue for this sender channel."""
        self.msg_queue.put(msg)
        msgs_in_queue.labels(self.id, self.recv.id, self.recv.hostname).inc()

    def get_msg_from_queue(self):
        """Gets the next message from the queue

        If there is no message, None will be returned. Non-blocking method.
        """
        if self.msg_queue.empty():
            return None
        msg = self.msg_queue.get()
        msgs_in_queue.labels(self.id, self.recv.id, self.recv.hostname).dec()
        return msg

    async def start(self):
        """Main loop for the sender channel."""
        while True:
            msg = self.get_msg_from_queue()
            if msg is None:
                await asyncio.sleep(0.01)
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
        # emit message sent message
        msgs_sent.labels(self.id).inc()
        msg = Message(MessageEnum.SENDER_MESSAGE, self.counter, self.id, data)
        sent_time = time.time()
        await self.socket.send(msg.as_bytes())

        reply_bytes = await self.socket.recv()
        # emit rtt time for sent and ACKed message
        msg_rtt.labels(self.id, self.recv.id, self.recv.hostname).set(
            time.time() - sent_time)
        try:
            reply_json = reply_bytes.decode()
            reply = jsonpickle.decode(reply_json)
            return reply
        except Exception as e:
            logger.error(f"error when decoding: {e}")
            return None
