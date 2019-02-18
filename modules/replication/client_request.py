"""Client request class and helpers.

A request q by client c is formed as a triple ⟨c, t, o⟩
where t is a totally-ordered timestamp (local to c) and o is the
requested operation.
"""


class ClientRequest:
    """Models a request as used in the Replication module."""

    def __init__(self, client_id, timestamp, operation):
        """Initializes a client request with the required data."""
        self.client_id = client_id
        self.timestamp = timestamp
        # TODO validate this in some way? should maybe add Operation class?
        self.operation = operation

    def get_client_id(self):
        """Returns the ID of the client that sent the reuest."""
        return self.client_id

    def get_timestamp(self):
        """Returns the local timestamp of the client that sent the request."""
        return self.timestamp

    def get_operation(self):
        """Returns the operation of the request, i.e. the RSM operation."""
        return self.operation
