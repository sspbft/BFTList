"""Models a receiver in the self-stabilizing communication protocol.

Each node sets up one receiver which the senders on all other nodes in the
system connect to.
"""

# standard
import socket
import logging

# local
from communication.udp.message import Message

logger = logging.getLogger(__name__)


class Receiver:
    """Models a receiver in the self-stabilizing communication protocol."""

    def __init__(self, ip, port, buf_size=1024, on_message_recv=None):
        """Initializes the receiver."""
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
        """Main loop for the receiver

        This method listens on the bound socket and whenever there is data to
        be sent over the socket, it receives that data and checks that the
        attached msg_counter (token) for that sender is not the same as the
        previously received token. If so, it sends the token back and then
        to the resolver which routes it to the appropriate module.
        """
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
        """Receive a message over the socket

        Blocking method that returns whenever a message has been received
        over the bound socket.
        """
        msg_bytes, address = self.socket.recvfrom(1024)
        msg = Message.from_bytes(msg_bytes)

        self.msgs_recv += 1
        self.bytes_recv += len(msg_bytes)

        return (msg, address)

    def send(self, msg, addr):
        """Send a message over the socket

        Blocking helper method that sends a message over the socket to the
        specified address pair (host/ip:port).
        """
        self.socket.sendto(msg.to_bytes(), addr)
