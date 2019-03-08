"""TODO write me."""

# standard
import socket
import logging

# local
from communication.udp.message import Message

logger = logging.getLogger(__name__)


class Receiver:
    """TODO write me."""

    def __init__(self, ip, port, buf_size=1024, on_message_recv=None):
        """TODO write me."""
        self.ip = ip
        self.port = port
        self.addr = (ip, port)
        self.buf_size = buf_size
        self.on_message_recv = on_message_recv

        # setup socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.addr)
        logger.info(f"FD receiver listening on {self.addr}")

        # store msg_counter for each sender
        self.msg_counters = {}

        # metrics
        self.msgs_recv = 0
        self.bytes_recv = 0

    def listen(self):
        """TODO write me."""
        while True:
            # block until data is available over socket
            msg, addr = self.recv()

            sender_id = msg.get_sender_id()
            msg_counter = msg.get_msg_counter()
            # token arrives
            if sender_id not in self.msg_counters:
                self.msg_counters[sender_id] = -1

            # accept message if new token, otherwise send back
            if msg_counter != self.msg_counters[sender_id]:
                self.msg_counters[sender_id] = msg_counter
                # send back token to sender
                self.send(msg, addr)

                # call callback if supplied
                if msg.has_payload() and self.on_message_recv is not None:
                    self.on_message_recv(msg.get_payload())

            else:
                # if token already received, send back token to sender
                self.send(msg, addr)

    def recv(self):
        """TODO write me."""
        msg_bytes, address = self.socket.recvfrom(1024)
        msg = Message.from_bytes(msg_bytes)

        self.msgs_recv += 1
        self.bytes_recv += len(msg_bytes)

        return (msg, address)

    def send(self, msg, addr):
        """TODO write me."""
        self.socket.sendto(msg.to_bytes(), addr)
