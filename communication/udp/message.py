"""TODO write me."""

# standard
import jsonpickle


class Message:
    """TODO write me."""
    def __init__(self, sender_id, msg_counter, payload={}):
        """TODO write me."""
        self.sender_id = sender_id
        self.msg_counter = msg_counter
        self.payload = payload

    def from_bytes(bytes):
        """TODO write me."""
        return jsonpickle.decode(bytes.decode())

    def to_bytes(self):
        """TODO write me."""
        return jsonpickle.encode(self).encode()

    def get_sender_id(self):
        """TODO write me."""
        return self.sender_id

    def get_msg_counter(self):
        """TODO write me."""
        return self.msg_counter

    def get_payload(self):
        """TODO write me."""
        return self.payload