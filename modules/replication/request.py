"""Request class and helpers.

An assigned request takes the form req = ⟨(request) q, (view) v,
(seq. num.) sq⟩.
"""

from client_request import ClientRequest


class Request:
    """Models a request as used in the Replication module."""

    def __init__(self, client_request: ClientRequest, view: int, seq_num: int):
        """Initializes a request object."""
        if type(client_request) != ClientRequest:
            raise ValueError("Arg client_request must be a ClientRequest")
        self.client_request = client_request
        self.view = view
        self.seq_num = seq_num

    def get_client_request(self):
        """Returns the client request associated with this request."""
        return self.client_request

    def get_view(self):
        """Returns the view associated with this request."""
        return self.view

    def get_seq_num(self):
        """Returns the sequence number associated with this request."""
        return self.seq_num
