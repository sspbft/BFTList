"""Client request class and helpers.

A request q by client c is formed as a triple ⟨c, t, o⟩
where t is a totally-ordered timestamp (local to c) and o is the
requested operation.
"""

# local
from .operation import Operation


class ClientRequest:
    """Models a request as used in the Replication module."""

    def __init__(self, client_id, timestamp, operation: Operation):
        """Initializes a client request with the required data."""
        self.client_id = client_id
        self.timestamp = timestamp
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

    def __str__(self):
        """Overrides the default implementation"""
        return (f"ClientRequest - client_id: {self.client_id}, timestamp: " +
                f"{self.timestamp}, operation: {self.operation}")

    def __eq__(self, other):
        """Overrides the default implementation"""
        if type(other) is type(self):
            return (self.client_id == other.get_client_id() and
                    self.timestamp == other.get_timestamp() and
                    self.operation == other.get_operation())
        return False

    def to_dct(self):
        """Converts a client request to a corresponding dictionary."""
        return {"client_id": self.client_id, "timestamp": self.timestamp,
                "operation": self.operation}
