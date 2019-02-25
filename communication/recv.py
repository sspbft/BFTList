"""Self-stabilizing asynchronous receiver channel."""

# standard
import asyncio
import io
import jsonpickle
import os
import logging
import socket
import struct

# local
from .pack_helper import PackHelper

# globals
logger = logging.getLogger(__name__)


class Receiver():
    """Models a self-stabilizing receiver channel."""

    def __init__(self, ip, port, resolver, chunks_size=1024):
        """Initializes the receiver channel."""
        self.port = port
        self.ip = ip
        self.host = socket.gethostname()
        self.chunks_size = chunks_size
        self.id = int(os.getenv("ID"))
        self.resolver = resolver
        self.pack_helper = PackHelper()

        self.tokens = {}
        self.token_size = struct.calcsize("iii")
        self.loop = asyncio.get_event_loop()

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.setblocking(False)
        self.tcp_socket.bind((ip, int(port)))
        self.tcp_socket.listen()

    async def tcp_listen(self):
        """Wait for tcp connections to arrive."""
        logger.debug(f"Listening for TCP connections on {self.ip}:{self.port}")
        while True:
            conn, addr = await self.loop.sock_accept(self.tcp_socket)
            logger.debug(f"Got TCP connection from {addr}")
            asyncio.ensure_future(self.tcp_response(conn))

    async def tcp_response(self, conn):
        """Receive tcp stream, create response and send it."""
        int_size = struct.calcsize("i")
        recv_msg_size = await self.loop.sock_recv(conn, int_size)
        try:
            msg_size = struct.unpack("i", recv_msg_size)[0]
        except Exception as e:
            logger.error(e)
            conn.close()
            return
        res = b''
        while (len(res) < msg_size):
            res += await self.loop.sock_recv(conn, self.chunks_size)
            await asyncio.sleep(0)

        response = await self.check_msg(res)
        response_stream = io.BytesIO(response)
        stream = True
        while stream:
            stream = response_stream.read(self.chunks_size)
            try:
                await self.loop.sock_sendall(conn, stream)
            except Exception as e:
                logger.error(e)
                conn.close()
                return
        conn.close()
        logger.debug("Connection closed")

    async def check_msg(self, res):
        """Determine message type and create response message accordingly."""
        token = res[:self.token_size]
        payload = res[self.token_size:]
        msg_type, msg_cntr, sender = struct.unpack("iii", token)

        try:
            msg_json = self.pack_helper.unpack(payload)[0][0]
            msg = jsonpickle.decode(msg_json.decode())

            # dispatch message to correct module through resolver
            self.resolver.dispatch_msg(msg)

            logger.debug(f"Received msg {msg} from node {sender}")
        except struct.error:
            logger.debug(f"Error: Could not unpack {payload}")

        if(sender not in self.tokens.keys()):
            logger.debug(f"Received token from new sender with id {sender}")
            self.tokens[sender] = 0

        if(self.tokens[sender] != msg_cntr):
            logger.debug(f"Got incremented token {msg_cntr} from " +
                         f"node {sender}")
            self.tokens[sender] = msg_cntr
        else:
            logger.debug(f"Received same token {msg_cntr} from {sender}")

        token = struct.pack("iii", msg_type, self.tokens[sender], self.id)
        return token
