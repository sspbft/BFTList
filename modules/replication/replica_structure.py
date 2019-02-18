"""Replica structure class and helpers.

The replica’s structure rep[n] = ⟨(replica state) repState, (executed req. log)
rLog, (pending req. queue) pendReqs, (requests under process queue) reqQ,
(last per client executed request) lastReq, (last assigned sq. num.) seqn,
(conflict flag) conFlag⟩, where repState is the replica’s state
(the replicate) which is an ordered sequence log.
"""

from typings import List, Dict

from modules.constants import (REQUEST, REPLY, STATUS)
from request import Request


class ReplicaStructure():
    """Models a replica structure as used in the Replication module."""

    def __init__(self, id, rep_state=[], r_log=[],
                 pend_reqs=[], req_q=[], last_req=[],
                 seq_num=-1, con_flag=False, view_changed=False, prim=-1):
        """."""
        self.id = id
        self.rep_state = rep_state
        self.r_log = r_log
        self.pend_reqs = pend_reqs
        self.req_q = req_q
        self.last_req = last_req
        self.seq_num = seq_num
        self.con_flag = con_flag
        self.view_changed = view_changed
        self.prim = prim

    def get_id(self) -> int:
        """Returns the id associated with this processor."""
        return self.id

    def get_rep_state(self):
        """Returns the state reported by this processor."""
        return self.rep_state

    def set_rep_state(self, rep_state):
        """Returns the state reported by this processor."""
        self.rep_state = rep_state

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
        self.validate_req_pair(req_pair)
        self.r_log.append(req_pair)

    def get_pend_reqs(self) -> List[Request]:
        """Returns the requests received from clients, all ClientRequests

        pend_reqs has size SIGMA * K, where SIGMA is a user-defined constant
        and K is the size of the clients set.
        """
        return self.pend_reqs

    def extend_pend_reqs(self, req: Request):
        """Adds a request to pend_reqs."""
        self.pend_reqs.extend(req)

    def remove_from_pend_reqs(self, req: Request):
        """Removes the first occurrence of req from pend_reqs."""
        self.pend_reqs.remove(req)

    def set_pend_reqs(self, pend_reqs: List[Request]):
        """Sets the pend_reqs for this processor."""
        self.pend_reqs = pend_reqs

    def get_req_q(self) -> List[Dict]:
        """Returns the requests that are in process along with their status."""
        return self.req_q

    def add_to_req_q(self, req_pair: Dict):
        """Adds a request pair to the req_q."""
        self.validate_req_pair(req_pair)
        self.req_q.append(req_pair)

    def remove_from_req_q(self, req):
        """Removes all occurrences of req from req_q."""
        self.req_q = [x for x in self.req_q if x[REQUEST] != req]

    def get_last_req(self) -> List[Dict]:
        """Returns a list of the last executed request for each client

        last_req[i] corresponds to request/reply of the last executed
        request for client with id i --> {REQUEST: req, REPLY: reply}
        """
        return self.last_req

    def update_last_req(self, client_id: int, request: Request, reply):
        """Update the last executed request for client with client_id."""
        self.last_req[client_id] = {
            REQUEST: request, REPLY: reply
        }

    def get_seq_num(self) -> int:
        """Returns the last assigned sequence number for this processor."""
        return self.seq_num

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

    # NOTE that def_state and tee should maybe not always be the same
    def is_def_state(self) -> bool:
        """Returns True if all processor data is set to default."""
        # TODO returns True if state == DEF_STATE
        pass

    def is_rep_state_default(self) -> bool:
        """Returns True if the processors state is set to default."""
        return self.rep_state == []

    def reset_state(self):
        """Resets the entire replica_structure to its default."""
        # TODO sets own state to DEF_STATE
        pass

    def is_tee(self) -> bool:
        """Returns True if the entire state corresponds to TEE."""
        # TODO returns True if state == DEF_STATE
        pass

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
