from modules.replication.models.operation import Operation
from modules.enums import OperationEnums

op = Operation(OperationEnums.APPEND, 1)
op2 = Operation(OperationEnums.APPEND, 2)
op3 = Operation(OperationEnums.APPEND, 3)
op4 = Operation(OperationEnums.POP, 1)

lst = []

lst = op.execute(lst)
lst = op2.execute(lst)
lst = op3.execute(lst)
lst = op4.execute(lst)

# list should be [1,3]
print(f"res: {lst}")