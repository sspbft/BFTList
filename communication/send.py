"""Self-stabilizing asynchronous sender channel."""
import asyncio
import io
import os
import socket
import struct


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
                msg = token  # resend token, will add payload here too
                await self.tcp_send(msg)
                print("TIMEOUT: no response within {}s".format(self.timeout))
        return (sender, msg_type, msg_cntr, msg_data)

    async def start(self):
        """Main loop for the sender channel."""
        counter = 1
        token = struct.pack("iii", self.ch_type, counter, self.id)
        await self.tcp_send(token)

        while True:
            token = struct.pack("iii", self.ch_type, counter, self.id)
            sender, msg_type, msg_cntr, msg_data = await self.receive(token)
            print("Token arrival: cntr is {}".format(msg_cntr))

            if(msg_cntr >= counter):
                counter = (msg_cntr + 1) % self.cap
                token = struct.pack("iii", self.ch_type, counter, self.id)
                msg = token  # msg = token + payload if payload is needed
                await self.tcp_send(msg)
                await asyncio.sleep(1)

    async def tcp_connect(self):
        """Creates a new TCP socket and waits until there is a connection."""
        if self.tcp_socket:
            self.tcp_socket.close()
        self.tcp_socket = socket.socket()
        self.tcp_socket.setblocking(False)
        while True:
            try:
                await self.loop.sock_connect(self.tcp_socket,
                                             (self.ip, self.port))
            except OSError as e:
                print("Node {}: Exception: {}".format(str(self.id), str(e)))
                print("Node {}: Trying to connect to ({}, {})".format(
                      str(self.id), self.ip, self.port))
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
