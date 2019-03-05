"""Code related to modelling of messages to be sent over comm links."""
from enum import Enum
import jsonpickle


class MessageEnum(Enum):
    """Enum representing a message type."""

    SENDER_MESSAGE = 0
    RECEIVER_MESSAGE = 1


class Message:
    """Models a Message to be sent over the communication channels."""

    def __init__(self, type, counter, sender_id, data={}):
        """Initializes a message."""
        self.type = type
        self.counter = counter
        self.sender_id = sender_id
        self.data = data

    def get_type(self):
        """Returns the type of the message."""
        return self.type

    def get_counter(self):
        """Returns the counter the message."""
        return self.counter

    def get_sender_id(self):
        """Returns the id of the sender the message."""
        return self.sender_id

    def get_data(self):
        """Returns the data (payload) of the message."""
        return self.data

    def as_json(self):
        """Returns JSON string representing this object."""
        return jsonpickle.encode(self)

    def as_bytes(self):
        """Returns byte representation of JSON string."""
        return str.encode(self.as_json())
