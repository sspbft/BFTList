"""Self-stabilizing asynchronous receiver channel."""
import asyncio
import io
import os
import socket
import struct


class Receiver():
    """Models a self-stabilizing receiver channel."""

    def __init__(self, port, ip, chunks_size=1024):
        """Initializes the receiver channel."""
        self.port = port
        self.ip = ip
        self.chunks_size = chunks_size
        self.id = int(os.getenv("ID"))

        self.tokens = {}
        self.token_size = 2 * struct.calcsize("i") + struct.calcsize("17s")
        self.loop = asyncio.get_event_loop()

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.setblocking(False)
        self.tcp_socket.bind((ip, int(port)))
        self.tcp_socket.listen()

    async def tcp_listen(self):
        """Wait for tcp connections to arrive."""
        print("Node {}: listening for tcp connections on {}:{}".
              format(str(self.id), self.ip, self.port))
        while True:
            conn, addr = await self.loop.sock_accept(self.tcp_socket)
            print("Node {}: {} got tcp connection from {}".
                  format(str(self.id), self.port, addr))
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
        if __debug__:
            print("Connection closed")

    async def check_msg(self, res):
        """Determine message type and create response message accordingly."""
        token = res[:self.token_size]
        payload = res[self.token_size:]
        msg_type, msg_cntr, sender = struct.unpack("ii17s", token)

        if(sender not in self.tokens.keys()):
            if __debug__:
                print("Node {}Adding new token".format(str(self.id)))
            self.tokens[sender] = 0

        if(self.tokens[sender] != msg_cntr):
            self.tokens[sender] = msg_cntr
            token = struct.pack("ii17s", msg_type, self.tokens[sender],
                                str(self.id).encode())
            if(msg_type == 0):
                if payload:
                    new_msg = await self.cb_obj.arrival(sender, payload)
                    if new_msg:
                        response = token + new_msg if new_msg else token
                    else:
                        response = token
                else:
                    response = token
            elif(msg_type == 1):
                raise NotImplementedError
        else:
            if __debug__:
                print("Node {}: NO TOKEN ARRIVAL".format(str(self.id)))
            token = struct.pack("ii17s", msg_type, self.tokens[sender],
                                str(self.id).encode())
            response = token
        return response
