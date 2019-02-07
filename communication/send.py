"""Self-stabilizing asynchronous sender channel."""

# standard
import asyncio
import logging
import io
import os
import socket
import struct
from queue import Queue

# local
from metrics.messages import msgs_sent

# globals
logger = logging.getLogger(__name__)


class Sender():
    """Models a self-stabilizing sender channel."""

    def __init__(self, ip, port, timeout=2, chunks_size=1024,
                 ch_type=0):
        """Initializes the sender channel."""
        self.port = port
        self.ip = ip
        self.addr = (ip, port)
        self.timeout = timeout
        self.chunks_size = chunks_size
        self.token_size = struct.calcsize("iii")
        self.id = int(os.getenv("ID"))
        self.msg_queue = Queue()

        self.ch_type = ch_type
        self.cap = 2**31
        self.tcp_socket = None
        self.loop = asyncio.get_event_loop()

    async def receive(self, token):
        """Waits for data over TCP for self.timeout seconds."""
        while True:
            try:
                res = await self.tcp_recv()
                token = res[:self.token_size]
                msg_type, msg_cntr, sender = struct.unpack("iii", token)
                msg_data = res[self.token_size:]
                break
            except Exception:
                logger.warning(f"TIMEOUT: no response in {self.timeout} s")
                # re-send message TODO add payload here and not send only token
                msg = token
                await self.tcp_send(msg)
        return (sender, msg_type, msg_cntr, msg_data)

    def add_msg_to_queue(self, msg):
        """Adds the message to the FIFO queue for this sender channel."""
        self.msg_queue.put(msg)

    async def get_msg_from_queue(self):
        """Gets the next message from the queue.

        Will block if there is no message to be sent.
        """
        while self.msg_queue.empty():
            continue
        msg = self.msg_queue.get()
        return msg

    async def start(self):
        """Main loop for the sender channel."""
        counter = 1
        token = struct.pack("iii", self.ch_type, counter, self.id)
        await self.tcp_send(token)

        while True:
            token = struct.pack("iii", self.ch_type, counter, self.id)
            sender, msg_type, msg_cntr, msg_data = await self.receive(token)
            logger.debug(f"Got back token {msg_cntr} from node {sender}")

            if(msg_cntr >= counter):
                counter = (msg_cntr + 1) % self.cap
                token = struct.pack("iii", self.ch_type, counter, self.id)
                payload = await self.get_msg_from_queue()
                msg = token + payload
                logger.debug(f"Incrementing counter to {counter} and " +
                             f"sending to node {self.addr}")
                await self.tcp_send(msg)
                self.msg_queue.task_done()
                # await asyncio.sleep(1)

    async def tcp_connect(self):
        """Creates a new TCP socket and waits until there is a connection."""
        if self.tcp_socket:
            self.tcp_socket.close()
        while True:
            self.tcp_socket = socket.socket()
            self.tcp_socket.setblocking(False)
            try:
                await self.loop.sock_connect(self.tcp_socket,
                                             (self.ip, self.port))
            except OSError as e:
                logger.error(f"Exception: {e} when connecting to {self.addr}")
                await asyncio.sleep(1)
            else:
                break

    async def tcp_send(self, msg):
        """Send tcp stream."""
        await self.tcp_connect()
        msg_size = struct.pack("i", len(msg))
        response_stream = io.BytesIO(msg_size + msg)
        stream = True
        while stream:
            stream = response_stream.read(self.chunks_size)
            await self.loop.sock_sendall(self.tcp_socket, stream)
        msgs_sent.labels(self.id).inc()

    async def tcp_recv(self):
        """Read a stream of tcp messages until the server closes the socket."""
        msg = b''
        while True:
            res_part = await asyncio.wait_for(
                self.loop.sock_recv(
                    self.tcp_socket, self.chunks_size), self.timeout)
            if not res_part:
                break
            else:
                msg += res_part
        return msg
