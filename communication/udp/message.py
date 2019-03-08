"""Models a message to be sent over the self-stabilizing communication link"""

# standard
import jsonpickle


class Message:
    """Models a message sent over the self-stabilizing communication link

    A message consists of a sender_id, msg_counter and eventual payload.
    The msg_counter is used by the sender/receiver to carry out the algorithm
    for token passing with sequence numbers proposed by Dolev.
    """

    def __init__(self, sender_id, msg_counter, payload={}):
        """Initializes a message"""
        self.sender_id = sender_id
        self.msg_counter = msg_counter
        self.payload = payload

    def from_bytes(bytes):
        """Decodes bytes object to a Message instance"""
        return jsonpickle.decode(bytes.decode())

    def to_bytes(self):
        """Encodes a Message instance to bytes"""
        return jsonpickle.encode(self).encode()

    def get_sender_id(self):
        """Returns the sender_id of the message"""
        return self.sender_id

    def get_msg_counter(self):
        """Returns the msg_counter (token) of the message"""
        return self.msg_counter

    def get_payload(self):
        """Returns the payload of the message"""
        return self.payload

    def has_payload(self):
        """Returns True if payload is attached to the message"""
        return self.payload != {}
