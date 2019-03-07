"""TODO write me."""

# standard
from threading import Thread
import socket
import logging
import time

# local
from communication.udp.message import Message
from modules.constants import FD_SLEEP, FD_TIMEOUT

logger = logging.getLogger(__name__)


class Sender:
    """TODO write me."""

    def __init__(self, id, addr, bufsize=1024, check_ready=None):
        """TODO write me."""
        self.id = id
        if type(addr) != tuple or type(addr[0]) != str or type(addr[1]) != int:
            raise ValueError(f"Arg addr must be tuple (ip, port)")
        self.addr = addr
        self.bufsize = bufsize
        self.check_ready = check_ready

        # setup socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.msg_counter = 0
        self.last_sent_msg = None
        self.last_recv_msg_counter = -1

    def start(self):
        """TODO write me."""
        # busy-wait on check_ready function if supplied
        if self.check_ready is not None and callable(self.check_ready):
            while not self.check_ready():
                pass

        msg = Message(self.id, self.msg_counter)
        self.send(msg)

        while True:
            # wait for token to arrive
            msg = self.recv()
            msg_counter = msg.get_msg_counter()
            self.last_recv_msg_counter = msg_counter

            # token arrives
            if msg_counter >= self.msg_counter:
                self.msg_counter += 1
                msg = Message(self.id, self.msg_counter)
                self.send(msg)
            else:
                # re-send last sent message
                self.send(self.last_sent_msg)
                logger.warning(f"Got invalid msg_counter {msg_counter} back")
            time.sleep(FD_SLEEP)

    def send(self, msg, timeout=True):
        """TODO write me."""
        self.socket.sendto(msg.to_bytes(), self.addr)
        self.last_sent_msg = msg

        if timeout:
            t = Thread(target=self.check_timeout, args=(msg,))
            t.start()

    def recv(self):
        """TODO write me."""
        msg_bytes = self.socket.recv(self.bufsize)
        msg = Message.from_bytes(msg_bytes)
        return msg

    def check_timeout(self, msg):
        """TODO write me."""
        start_time = time.time()
        msg_counter = msg.get_msg_counter()
        while time.time() - start_time < FD_TIMEOUT:
            if self.last_recv_msg_counter >= msg_counter:
                # token returned from receiver
                return
            else:
                time.sleep(FD_SLEEP)
        logger.info(f"Timeout, re-sending token {msg_counter}")
        self.send(msg, timeout=False)
        self.check_timeout(msg)
