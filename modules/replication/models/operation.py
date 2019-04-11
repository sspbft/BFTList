"""Module used to model operations that can be carried out on BFTList state."""

# standard
from typing import List

# local
from modules.enums import OperationEnums


class Operation(object):
    """Models operations that can be performed on the state

    Operations should be specified along with a list of arguments by clients
    when sending requests to BFTList.
    """

    def __init__(self, op_type: OperationEnums, *args):
        """Initializes an operation."""
        if type(op_type) == str:
            if op_type == "APPEND":
                op_type = OperationEnums.APPEND
            elif op_type == "NO_OP":
                op_type = OperationEnums.NO_OP
            else:
                raise ValueError(f"op_type {op_type} is not valid")
        if type(op_type) != OperationEnums:
            raise ValueError(f"op_type {op_type} is not a OperationEnum")
        self.op_type = op_type
        self.args = args

    def get_type(self):
        """Returns the type of operation to execute."""
        return self.op_type

    # BFTList only supports list operations for now
    def execute(self, lst: List):
        """Executes the specified operation on the supplied list."""
        if type(lst) != list:
            raise ValueError(f"Input {lst} is not a list")

        if self.op_type == OperationEnums.APPEND:
            lst.append(self.args[0])
        elif self.op_type == OperationEnums.NO_OP:
            return lst
        else:
            raise ValueError(f"Bad operation {self.type}")
        return lst

    def __str__(self):
        """Override the default __str__."""
        return f"Operation - type: {self.op_type}, args: {self.args}"

    def __eq__(self, other):
        """Overrides the default implementation"""
        if type(other) is type(self):
            return (self.get_type() == other.get_type() and
                    self.args == other.args)
        return False

    def to_dct(self):
        """Converts an operation to a corresponding dictionary."""
        return {"type": self.op_type.name, "args": list(self.args)}
