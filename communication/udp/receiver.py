"""TODO write me."""

# standard
import socket
import jsonpickle
import logging

# local
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
        logger.info(f"Receiver listening on {self.addr}")

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

            # acknowledge message to sender
            self.ack(msg, addr)

    def recv(self):
        """TODO write me."""
        msg_bytes, address = self.socket.recvfrom(1024)
        msg = jsonpickle.decode(msg_bytes.decode())

        sender_id = msg.get_sender_id()
        msg_counter = msg.get_msg_counter()
        # token arrives
        if sender_id not in self.msg_counters:
            self.msg_counters[sender_id] = msg_counter
        elif msg_counter != self.msg_counters[sender_id]:
            self.msg_counters[sender_id] = msg_counter

            self.msgs_recv += 1
            self.bytes_recv += len(msg_bytes)
            logger.info(f"{self.msgs_recv} msgs received")

            # call callback if supplied
            if self.on_message_recv is not None:
                self.on_message_recv(msg)
        else:
            # TODO do something here?
            pass

        return (msg, address)

    def ack(self, msg, addr):
        """TODO write me."""
        self.socket.sendto(msg.as_bytes(), addr)
