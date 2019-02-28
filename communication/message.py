from enum import Enum
import jsonpickle


class MessageEnum:
    SENDER_MESSAGE = 0
    RECEIVER_MESSAGE = 1


class Message:
    def __init__(self, type, counter, sender_id, data={}):
        self.type = type
        self.counter = counter
        self.sender_id = sender_id
        self.data = data
    
    def get_type(self):
        return self.type

    def get_counter(self):
        return self.counter

    def get_sender_id(self):
        return self.sender_id

    def get_data(self):
        return self.data

    def as_json(self):
        """Returns JSON string representing this object."""
        return jsonpickle.encode(self)

    def as_bytes(self):
        """Returns byte representation of JSON string."""
        return str.encode(self.as_json())