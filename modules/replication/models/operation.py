"""Module used to model operations that can be carried out on BFTList state."""

# standard
from typing import List

# local
from modules.enums import OperationEnums


class Operation:
    """Models operations that can be performed on the state

    Operations should be specified along with a list of arguments by clients
    when sending requests to BFTList.
    """

    def __init__(self, _type: OperationEnums, *args):
        """Initializes an operation."""
        self.type = _type
        self.args = args

    # BFTList only supports list operations for now
    def execute(self, lst: List):
        """Executes the specified operation on the supplied list."""
        if type(lst) != list:
            raise ValueError(f"Input {lst} is not a list")

        if self.type == OperationEnums.APPEND:
            lst.append(self.args[0])
        elif self.type == OperationEnums.POP:
            lst.pop(self.args[0])
        else:
            raise ValueError(f"Bad operation {self.type}")

        return lst

    def __str__(self):
        """Override the default __str__."""
        return f"Operation - type: {self.type}, args: {self.args}"

    def __eq__(self, other):
        """Overrides the default implementation"""
        if type(other) is type(self):
            return (self.type == other.type and
                    self.args == other.args)
        return False
