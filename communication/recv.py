"""Self-stabilizing asynchronous receiver channel."""
import asyncio
import io
import json
import os
import socket
import struct
from .pack_helper import PackHelper


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

    def log(self, msg):
        """Temporary logging method."""
        return
        print(f"Node {os.getenv('ID')}.Receiver: {msg}")

    async def tcp_listen(self):
        """Wait for tcp connections to arrive."""
        self.log(f"Listening for TCP connections on {self.ip}:{self.port}")
        while True:
            conn, addr = await self.loop.sock_accept(self.tcp_socket)
            self.log(f"Got TCP connection from {addr}")
            asyncio.ensure_future(self.tcp_response(conn))

    async def tcp_response(self, conn):
        """Receive tcp stream, create response and send it."""
        int_size = struct.calcsize("i")
        recv_msg_size = await self.loop.sock_recv(conn, int_size)
        try:
            msg_size = struct.unpack("i", recv_msg_size)[0]
        except Exception as e:
            print(e)
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
                print(e)
                conn.close()
                return
        conn.close()
        self.log("Connection closed")

    async def check_msg(self, res):
        """Determine message type and create response message accordingly."""
        token = res[:self.token_size]
        payload = res[self.token_size:]
        msg_type, msg_cntr, sender = struct.unpack("iii", token)
        try:
            msg_json = self.pack_helper.unpack(payload)[0][0]
            msg = json.loads(msg_json.decode())
            self.resolver.dispatch_msg(msg, sender)
            # self.log(f"Received msg {msg} from node {sender}")
        except struct.error:
            self.log(f"Error: Could not unpack {payload}")

        if(sender not in self.tokens.keys()):
            self.log(f"Received token from new sender with id {sender}")
            self.tokens[sender] = 0

        if(self.tokens[sender] != msg_cntr):
            self.log(f"Got incremented token {msg_cntr} from node {sender}")
            self.tokens[sender] = msg_cntr
        else:
            self.log(f"Received same token {msg_cntr} from {sender}")

        token = struct.pack("iii", msg_type, self.tokens[sender], self.id)
        return token
