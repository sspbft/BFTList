"""Models a sender in the self-stabilizing communication protocol.

Each node sets up n-1 senders that each connect to a receiver on the other
side of the communication link.
"""

# standard
from threading import Thread
import socket
import logging
import time
from queue import Queue
import sys

# local
from communication.udp.message import Message
from modules.constants import FD_SLEEP, FD_TIMEOUT

logger = logging.getLogger(__name__)
MAXINT = sys.maxsize
UDP = "UDP"


class Sender:
    """Models a sender in the self-stabilizing communication protocol."""

    def __init__(self, id, addr, cap=MAXINT, bufsize=1024, check_ready=None,
                 on_message_sent=None):
        """Initalizes the sender."""
        self.id = id
        if type(addr) != tuple or type(addr[0]) != str or type(addr[1]) != int:
            raise ValueError(f"Arg addr must be tuple (hostname, port)")
        self.addr = addr
        self.cap = cap
        self.bufsize = bufsize
        self.check_ready = check_ready
        self.on_message_sent = on_message_sent

        # setup socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.msg_counter = 0
        self.msg_queue = Queue()
        self.last_sent_msg = None
        self.last_recv_msg_counter = -1

    def add_msg_to_queue(self, msg):
        """Adds the message to the FIFO queue for this sender channel."""
        self.msg_queue.put(msg)

    def get_msg_from_queue(self):
        """Gets the next message from the queue

        If there is no message, None will be returned. Non-blocking method.
        """
        if self.msg_queue.empty():
            return None
        msg = self.msg_queue.get()
        return msg

    def start(self):
        """Main loop for the sender

        This is the main loop of the sender in the self-stabilizing
        token-passing algorithm with bounded sequence number proposed by Dolev.
        It uses a token attached to each message which is sent back and forth
        between the sender and receiver. Payload can be attached to
        the messages to exchange application-level data.
        """
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
                # busy wait until there is a new message to send
                while self.msg_queue.empty():
                    time.sleep(0.1)

                msg = self.get_msg_from_queue()
                self.msg_counter += 1 % self.cap
                fd_msg = Message(self.id, self.msg_counter, payload=msg)
                self.send(fd_msg)
            else:
                # re-send last sent message
                self.send(self.last_sent_msg)
                logger.warning(f"Got invalid msg_counter {msg_counter} back")
            time.sleep(FD_SLEEP)

    def send(self, msg, timeout=True):
        """Sends a message over the link to the receiver

        Helper method that blocks until the message is sent to the receiver.
        A thread is launched that monitors the return of the token of the
        message, which will eventually re-send the message if needed.
        """
        msg_as_bytes = msg.to_bytes()
        self.socket.sendto(msg_as_bytes, self.addr)
        self.last_sent_msg = msg
        # Emit size of sent message

        if self.on_message_sent is not None:
            metric_data = {"bytes_size": len(msg_as_bytes),
                           "msg_type": UDP}
            self.on_message_sent(msg.get_payload(), metric_data)

        if timeout:
            t = Thread(target=self.check_timeout, args=(msg,))
            t.start()

    def recv(self):
        """Receives a message from the receiver

        Helper method that blocks until a message is received from the
        receiver.
        """
        msg_bytes = self.socket.recv(self.bufsize)
        msg = Message.from_bytes(msg_bytes)
        return msg

    def check_timeout(self, msg):
        """Helper method that re-sends a message if needed

        If the token sent is not recevied within FD_TIMEOUT seconds, the
        message is re-sent.
        """
        start_time = time.time()
        msg_counter = msg.get_msg_counter()
        while time.time() - start_time < FD_TIMEOUT:
            if self.last_recv_msg_counter >= msg_counter:
                # token returned from receiver
                return
            else:
                time.sleep(FD_SLEEP)
        logger.warning(f"Timeout, re-sending msg {msg_counter} to {self.addr}")
        self.send(msg, timeout=False)
        self.check_timeout(msg)
