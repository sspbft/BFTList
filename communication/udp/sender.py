"""TODO write me."""

# standard
import socket
import logging
import jsonpickle

# local
from communication.udp.message import Message

logger = logging.getLogger(__name__)


class Sender:
    """TODO write me."""

    def __init__(self, id, addr, bufsize=1024):
        """TODO write me."""
        self.id = id
        if type(addr) != tuple or type(addr[0]) != str or type(addr[1]) != int:
            raise ValueError(f"Arg addr must be tuple (ip, port)")
        self.addr = addr
        self.bufsize = bufsize

        # setup socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.msg_counter = 0

    def start(self):
        """TODO write me."""
        msg = Message(self.id, self.msg_counter)
        self.send(msg)

        while True:
            # wait for token to arrive
            msg_counter = self.recv()
            # token arrives
            if msg_counter >= self.msg_counter:
                # logger.info(f"FDSender {self.addr} got back token {msg_counter}")
                self.msg_counter += 1
                msg = Message(self.id, self.msg_counter)
                self.send(msg)
            else:
                # TODO do something more here? re-send?
                logger.warning(f"Got invalid msg_counter {msg_counter} back")

    def send(self, msg):
        """TODO write me."""
        self.socket.sendto(msg.as_bytes(), self.addr)

    def recv(self):
        """TODO write me."""
        msg_bytes = self.socket.recv(self.bufsize)
        msg = jsonpickle.decode(msg_bytes.decode())
        return msg.get_msg_counter()
