"""Replica structure class and helpers.

The replica’s structure rep[n] = ⟨(replica state) repState, (executed req. log)
rLog, (pending req. queue) pendReqs, (requests under process queue) reqQ,
(last per client executed request) lastReq, (last assigned sq. num.) seqn,
(conflict flag) conFlag⟩, where repState is the replica’s state
(the replicate) which is an ordered sequence log.
"""

# standard
from typing import List, Dict
from copy import deepcopy

# local
from modules.constants import (REQUEST, REPLY, STATUS, X_SET)
from .request import Request, ClientRequest


class ReplicaStructure(object):
    """Models a replica structure as used in the Replication module."""

    def __init__(self, id, number_of_clients=1, rep_state=[], r_log=[],
                 pend_reqs=[], req_q=[], last_req=[],
                 seq_num=-1, con_flag=False, view_changed=False, prim=0):
        """Initializes a replica structure with its default state."""
        self.id = id
        self.rep_state = deepcopy(rep_state)
        self.r_log = deepcopy(r_log)
        self.pend_reqs = deepcopy(pend_reqs)
        self.req_q = deepcopy(req_q)
        if last_req == []:
            self.last_req = [-1 for i in range(number_of_clients)]
        else:
            self.last_req = deepcopy(last_req)
        self.seq_num = seq_num
        self.con_flag = con_flag
        self.view_changed = view_changed
        self.prim = prim

    def set_replica_structure(self, rs):
        """Setting some of the replica structure to the input rs."""
        self.rep_state = deepcopy(rs.get_rep_state())
        self.r_log = deepcopy(rs.get_r_log())
        self.pend_reqs = deepcopy(rs.get_pend_reqs())
        self.req_q = deepcopy(rs.get_req_q())
        self.last_req = deepcopy(rs.get_last_req())
        self.seq_num = deepcopy(rs.get_seq_num())
        self.con_flag = False
        self.view_changed = False
        self.prim = deepcopy(rs.get_prim())

    def get_id(self) -> int:
        """Returns the id associated with this processor."""
        return self.id

    def get_rep_state(self):
        """Returns the state reported by this processor."""
        return self.rep_state

    def set_rep_state(self, rep_state):
        """Returns the state reported by this processor."""
        self.rep_state = deepcopy(rep_state)

    def get_r_log(self) -> List[Dict]:
        """Returns the request execution log

        An entry in r_log is a dictionary { req: request, xSet: set of nodes }
        where xSet are the nodes claiming to have executed req
        """
        return self.r_log

    def add_to_r_log(self, req_pair: Dict):
        """Adds the request pair to r_log.

        req_pair is a dict according to the following scheme
        { REQUEST: req, STATUS: set(st) : st ∈ ⟨PRE−PREP, PREP, COMMIT⟩},
        where req is of type Request
        """
        self.validate_log_entry(req_pair)
        self.r_log.append(req_pair)

    def set_r_log(self, r_log: List):
        """Sets the r_log for this processor.

        NOTE that no validation of r_log is done, this is mainly used for
        testing purposes.
        """
        self.r_log = deepcopy(r_log)

    def exist_in_r_log(self, req: Request):
        """Returns true if request exist in r_log."""
        for applied_req in self.r_log:
            if applied_req[REQUEST] == req:
                return True
        return False

    def get_pend_reqs(self) -> List[ClientRequest]:
        """Returns the requests received from clients, all ClientRequests

        pend_reqs has size SIGMA * K, where SIGMA is a user-defined constant
        and K is the size of the clients set.
        """
        return self.pend_reqs

    def extend_pend_reqs(self, req: [ClientRequest]):
        """Adds a list of ClientRequests to pend_reqs."""
        for r in req:
            if r not in self.pend_reqs:
                self.pend_reqs.append(deepcopy(r))

    def remove_from_pend_reqs(self, req: ClientRequest):
        """Removes the first occurrence of req from pend_reqs."""
        if req in self.pend_reqs:
            self.pend_reqs.remove(req)

    def set_pend_reqs(self, pend_reqs: List[ClientRequest]):
        """Sets the pend_reqs for this processor."""
        self.pend_reqs = deepcopy(pend_reqs)

    def set_req_q(self, req_q: List[Dict]):
        """Sets the req_q for this processor.

        NOTE that no validation is done on the performed req_q. This is mainly
        used for testing purposes.
        """
        self.req_q = deepcopy(req_q)

    def get_req_q(self) -> List[Dict]:
        """Returns the requests that are in process along with their status."""
        return self.req_q

    def add_to_req_q(self, req_pair: Dict):
        """Adds a request pair to the req_q."""
        self.validate_req_pair(req_pair)
        if not self.req_already_exist(req_pair[REQUEST]):
            self.req_q.append(deepcopy(req_pair))

    def req_already_exist(self, req: Request):
        """Checks if the request exist in req_q."""
        for req_pair in self.req_q:
            if req_pair[REQUEST] == req:
                return True
        return False

    def remove_from_req_q(self, req):
        """Removes all occurrences of req from req_q."""
        self.req_q = [x for x in self.req_q if x[REQUEST] != req]

    def get_last_req(self) -> List:
        """Returns a list of the last executed requests for each client

        last_req[i] corresponds to request/reply of the last executed
        request for client with id i --> {REQUEST: req, REPLY: reply}
        """
        return self.last_req

    def update_last_req(self, client_id: int, request: Request, reply):
        """Update the last executed request for client with client_id."""
        # print(f"Setting last_req to {client_id}, {request} {reply}")
        # self.last_req[int(client_id)] = {
        #     REQUEST: deepcopy(request), REPLY: deepcopy(reply)
        # }
        # Account for dynamic size of client set
        for i in range(client_id + 1):
            if len(self.last_req) < i:
                self.last_req.append(None)
        self.last_req[client_id] = {REQUEST: request, REPLY: reply}

    def get_seq_num(self) -> int:
        """Returns the last assigned sequence number for this processor."""
        return self.seq_num

    def inc_seq_num(self):
        """Increments the sequence number by 1 for this processor."""
        self.seq_num += 1

    def set_seq_num(self, seq_num: int):
        """Sets the sequence number for this processor."""
        self.seq_num = seq_num

    def get_con_flag(self) -> bool:
        """Returns whether this processor has flagged for conflict."""
        return self.con_flag

    def set_con_flag(self, con_flag: bool):
        """Updates the con_flag value of this processor."""
        self.con_flag = con_flag

    def get_view_changed(self) -> bool:
        """Returns True if this processor has done a view change."""
        return self.view_changed

    def set_view_changed(self, view_changed: bool):
        """Update view_changed of this processor."""
        self.view_changed = view_changed

    def get_prim(self) -> int:
        """Returns what processor this processor considers to be prim."""
        return self.prim

    def set_prim(self, prim: int):
        """Update what node this processor considers to be the primary."""
        self.prim = prim

    def is_def_prefix(self) -> bool:
        """Returns True if data used for prefix finding is set to default."""
        return (self.rep_state == [] and self.r_log == [] and
                self.pend_reqs == [] and self.req_q == [])

    def is_def_state(self) -> bool:
        """Returns True if all processor data is set to default."""
        return (self.rep_state == [] and self.r_log == [] and
                self.pend_reqs == [] and self.req_q == [] and
                self.last_req == {} and self.seq_num == 0 and
                self.con_flag is False and self.view_changed is False and
                self.prim == 0)

    def is_rep_state_default(self) -> bool:
        """Returns True if the processors state is set to default."""
        return self.rep_state == []

    def reset_state(self):
        """Resets the entire replica_structure to its default."""
        self.__init__(self.id)

    def set_to_tee(self):
        """Sets the entire replica structure to TEE."""
        self.rep_state = []
        self.r_log = []
        self.pend_reqs = []
        self.req_q = []
        self.last_req = {}
        self.seq_num = -1
        self.con_flag = False
        self.view_changed = False
        self.prim = -1

    def is_tee(self) -> bool:
        """Returns True if the entire state corresponds to TEE.

        This means that the current state of this replica is the default.
        """
        return (self.rep_state == [] and self.r_log == [] and
                self.pend_reqs == [] and self.req_q == [] and
                self.last_req == {} and self.seq_num == -1 and
                self.con_flag is False and self.view_changed is False and
                self.prim == -1)

    def validate_req_pair(self, req_pair: Dict):
        """Validates a request pair.

        A request_pair is structured as follows:
        { REQUEST: req, STATUS: set(st) : st ∈ ⟨PRE−PREP, PREP, COMMIT⟩},
        where req is of type Request.
        """
        if REQUEST not in req_pair or STATUS not in req_pair:
            raise ValueError(f"req_pair {req_pair} is invalid")
        req = req_pair[REQUEST]
        status = req_pair[STATUS]
        if type(req) != Request or type(status) != set:
            raise ValueError(f"Illegal values in req_pair dict")

    def validate_log_entry(self, log_entry: Dict):
        """Validates a request log entry.

        A request_pair is structured as follows:
        { REQUEST: req, X_SET: set([x]) : x is a processor id},
        where req is of type Request.
        """
        if REQUEST not in log_entry or X_SET not in log_entry:
            raise ValueError(f"log_entry {log_entry} is invalid")
        req = log_entry[REQUEST]
        x_set = log_entry[X_SET]
        if type(req) != Request or type(x_set) != set:
            raise ValueError(f"Illegal values in log_entry dict")

    def __eq__(self, other):
        """Overrides the default implementation."""
        if type(other) == type(self):
            return (self.rep_state == other.get_rep_state() and
                    self.r_log == other.get_r_log() and
                    self.pend_reqs == other.get_pend_reqs() and
                    self.req_q == other.get_req_q() and
                    self.last_req == other.get_last_req() and
                    self.seq_num == other.get_seq_num() and
                    self.con_flag == other.get_con_flag() and
                    self.view_changed == other.get_view_changed() and
                    self.prim == other.get_prim())

    def __str__(self):
        """Override default __str__."""
        return f"ReplicaStructure: id: {self.id}, rep_state:" + \
               f" {self.rep_state}, r_log: {self.r_log}, pend_reqs: " + \
               f"{self.pend_reqs}, req_q: {self.req_q}, last_req: " + \
               f"{self.last_req}, seq_num: {self.seq_num}, con_flag: " + \
               f"{self.con_flag}, view_changed: {self.view_changed}" + \
               f", prim: {self.prim}"
