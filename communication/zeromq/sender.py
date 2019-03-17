"""Asynchronous sender channel."""

# standard
import asyncio
import logging
import zmq
import time
import zmq.asyncio
from queue import Queue
import jsonpickle

# local
from metrics.messages import msgs_in_queue
from .message import Message, MessageEnum
import modules.byzantine as byz
from communication.constants import ZERO_MQ

# globals
logger = logging.getLogger(__name__)


class Sender():
    """Models a sender channel for the zeromq/TCP protocol.

    The sender setsconnects to a receiver that runs a zeromq server in
    order to send messages.
    """

    def __init__(self, id, node, on_message_sent=None):
        """Initializes the sender."""
        self.id = id
        self.recv = node
        self.on_message_sent = on_message_sent

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
                # busy-wait if node is unresponsive before sending message
                while byz.is_unresponsive():
                    time.sleep(0.1)

                reply = await self.send(msg)
                if reply.get_counter() != self.counter:
                    raise ValueError("did not get same counter back")
                self.counter += 1 % self.cap

    async def send(self, data):
        """Sends a message over the specified channel.

        Constructs a message consisting of the token and the payload and sends
        it over the socket.
        """
        msg = Message(MessageEnum.SENDER_MESSAGE, self.counter, self.id, data)
        sent_time = time.time()
        msg_as_bytes = msg.as_bytes()
        await self.socket.send(msg_as_bytes)

        reply_bytes = await self.socket.recv()
        # metric rtt time for sent and ACKed message
        latency = time.time() - sent_time

        if self.on_message_sent is not None:
            metric_data = {"rec_id": self.recv.id,
                           "rec_hostname": self.recv.hostname,
                           "latency": latency,
                           "bytes_size": len(msg_as_bytes),
                           "msg_type": ZERO_MQ}
            self.on_message_sent(data, metric_data)

        try:
            reply_json = reply_bytes.decode()
            reply = jsonpickle.decode(reply_json)
            return reply
        except Exception as e:
            logger.error(f"error when decoding: {e}")
            return None
