"""Request class and helpers.

An assigned request takes the form req = ⟨(request) q, (view) v,
(seq. num.) sq⟩.
"""

# local
from .client_request import ClientRequest


class Request(object):
    """Models a request as used in the Replication module."""

    def __init__(self, client_request: ClientRequest, view: int, seq_num: int):
        """Initializes a request object."""
        if type(client_request) != ClientRequest:
            raise ValueError("Arg client_request must be a ClientRequest")
        self.client_request = client_request
        self.view = view
        self.seq_num = seq_num

    def get_client_request(self) -> ClientRequest:
        """Returns the client request associated with this request."""
        return self.client_request

    def get_view(self) -> int:
        """Returns the view associated with this request."""
        return self.view

    def set_view(self, view: int):
        """Updates the view of this request."""
        self.view = view

    def get_seq_num(self) -> int:
        """Returns the sequence number associated with this request."""
        return self.seq_num

    def set_seq_num(self, seq_num: int):
        """Returns the sequence number associated with this request."""
        self.seq_num = seq_num

    def __eq__(self, other):
        """Overrides the default implementation."""
        if type(other) == type(self):
            return (self.client_request == other.get_client_request() and
                    self.view == other.get_view() and
                    self.seq_num == other.get_seq_num())
        return False

    def __str__(self):
        """Overrides the default implementation."""
        return (f"Request - client_request: {str(self.client_request)}, " +
                f"view: {self.view}, seq_num: {self.seq_num}")

    def __hash__(self):
        """Overrides the default implementation"""
        return hash((self.client_request.get_client_id(),
                    self.view,
                    self.seq_num))

    def to_dct(self):
        """Converts a request to a corresponding dictionary."""
        return {"client_request": self.client_request.to_dct(),
                "view": self.view, "seq_num": self.seq_num}
