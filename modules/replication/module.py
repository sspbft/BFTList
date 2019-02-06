"""Contains code related to the Replication module."""

import time
from modules.algorithm_module import AlgorithmModule
# from modules.enums import ReplicationEnums
from modules.constants import (REP_STATE, R_LOG, PEND_REQS, REQ_Q,
                               LAST_REQ, CON_FLAG, VIEW_CHANGE,
                               REQUEST, SEQUENCE_NO, STATUS)  # X_SET, REPLY
from copy import deepcopy


class ReplicationModule(AlgorithmModule):
    """Models the Replication module.

    Structure of variables:
    q (request by client): <client c, timestamp t, operation o>
    request (accepted request): < request q, view v, sequence number seq_n>
    rep_state = UNDEFINED
    r_log (x_set is the set that claim to have executed/comitted request):
        <request, x_set>
    pend_req: <request>
    req_q : <request, status t>
    last_req: (last executed request for each client): <request, reply>

    rep[n] (replica structure):
        <rep_state, r_log, pend_req, req_q, last_req, con_flag, view_change>
    """

    def __init__(self, id, resolver, n, f):
        """Initializes the module."""
        self.id = id
        self.resolver = resolver
        self.number_of_nodes = n
        self.number_of_byzantine = f
        self.DEF_STATE = {REP_STATE: {},
                          R_LOG: [],
                          PEND_REQS: [],
                          REQ_Q: [],
                          LAST_REQ: [],
                          CON_FLAG: False,
                          VIEW_CHANGE: False}

        self.flush = False
        self.need_flush = False
        self.seq_n = 0
        self.rep = [
            {REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
             VIEW_CHANGE: False}
            for i in range(n)
        ]
        self.prim = None

    def run(self):
        """Called whenever the module is launched in a separate thread."""
        while True:
            time.sleep(1.5)

    # Macros

    def flush_local(self):
        """Resets all local variables."""
        self.seq_n = 0
        self.rep = [deepcopy(self.DEF_STATE) for i in range(
                                                        self.number_of_nodes)]

    def msg(self, status, processor_j):
        """Returns requests reported to p_i from processor_j with status."""
        request_set = set()
        for request_pair in self.rep[processor_j].get(REQ_Q):
            if request_pair.get(STATUS) == status:
                request_set.add(request_pair.get(REQUEST))
        return request_set

    def last_exec(self):
        """Returns last request (highest sequence number) executed."""
        last_execution = {REQUEST: {SEQUENCE_NO: -1}}  # Dummy request
        for request_pair in self.rep[self.id].get(R_LOG):
            if(request_pair.get(REQUEST).get(SEQUENCE_NO) >
               last_execution.get(REQUEST).get(SEQUENCE_NO)):
                last_execution = deepcopy(request_pair)
        return last_execution

    def last_common_exec(self):
        """Method description.

        Returns last request sequence number executed by at least 3f+1
        processors.
        """
        raise NotImplementedError

    def conflict(self):
        """Returns true if 4f+1 processors has conFlag to true."""
        raise NotImplementedError

    def com_pref_states(self, required_processors):
        """Method description.

        Returns a set of replica states which has a prefix at at least
        required_processors. Returns empty if not.
        """
        raise NotImplementedError

    def get_ds_state(self):
        """Method description.

        Returns a prefix if suggested by at least 2f+1 and at most 3f+1
        processors, and if there exists another set with the default
        replica state and these two sets adds up to at least 4f+1 processors.
        """
        raise NotImplementedError

    def double(self):
        """Method description.

        Returns true if request queue contains two copies of a request with
        different sequence numbers or views.
        """
        raise NotImplementedError

    def stale_req_seqn(self):
        """Returns true if the sequence number has reached its limit."""
        raise NotImplementedError

    def unsup_req(self):
        """Method description.

        Returns true if a request exists in request queue less than
        2f+1 times (the request is unsupported).
        """
        raise NotImplementedError

    def stale_rep(self):
        """Returns true if double(), unsup_req or stale_req_seqn is true."""
        raise NotImplementedError

    def known_pend_reqs(self):
        """Method description.

        Returns the set of requests in request queue and in the message queue
        of 3f+1 other processors.
        """
        raise NotImplementedError

    def known_reqs(self, status):
        """Method description.

        Returns the set of requests in request queue and in the message queue
        of 3f+1 other processors with status.
        """
        raise NotImplementedError

    def delayed(self):
        """Method description.

        Returns true if the last executed request is smaller than last common
        executed request plus
        3*cardinality size of the clients set*defined integer constant(3Ksigma)
        """
        raise NotImplementedError

    def exists_preprep_msg(self, request, prim):
        """Method description.

        Returns true if there exists a PRE_PREP msg from the primary
        for the request.
        """
        raise NotImplementedError

    def unassigned_reqs(self):
        """Method description.

        Returns set of pending requests without PRE_PREP msg or
        without having 3f+1 processors reported to have PREP msg
        for the requests.
        """
        raise NotImplementedError

    def accept_req_preprep(self, request, prim):
        """Method description.

        True if PRE_PREP msg from prim exists and the content is the same for
        3f+1 processors in the same view and sequence number.
        """
        raise NotImplementedError

    def committed_set(self, request):
        """Method description.

        Returns the set of processors that has reported to commit to the
        request and has the request in their executed request log.
        """
        raise NotImplementedError

    # Interface functions
    def get_pend_reqs(self):
        """Method description.

        Returns requests in pending request queue that has not been
        assigned a sequence number and appears in the request queue
        of other processors.
        """
        if not self.rep[self.id].get(VIEW_CHANGE):
            return(self.known_pend_reqs().intersection(self.unassigned_reqs()))
        # I will leave this else until the calling algorithm is
        # implemented and we can see how it will react
        # else:
            # return("view_change")

    def rep_request_reset(self):
        """Method description.

        Sets the need_flush flag to False by the View Establishment module
        after it has noted that a reset is required.
        Does not trigger a reset several times.
        """
        if self.need_flush:
            self.need_flush = False
            return True
        return False

    def replica_flush(self):
        """Method description.

        Sets the flag flush to true.
        The View Establishment module can demand a reset of the replica state.
        """
        self.flush = True

    # Functions not declared under macros and interface functions (Figure 6)
    def renew_reqs(self, processors_set):
        """Method description.

        Creates PRE_PREP msg for each request not being executed by
        4f+1 processors.
        """
        raise NotImplementedError

    def find_cons_state(self, processors_set):
        """Method description.

        Returns a consolidated replica state based on the processors_set,
        the set should have a common (non-empty) prefix and consistency
        among request and pending queues.
        Produces a dummy request if 3f+1 processor have committed a number
        of request without the existence of the previous request.
        """
        raise NotImplementedError

    def check_new_v_state(self, prim):
        """Method description.

        Check the state proposed by new primary.
        Checks if the PRE_PREP messages are verified by 3f+1 processors and
        that the new state has a correct prefix.
        """
        raise NotImplementedError

    # Function to extract data
    def get_data(self):
        """Returns current values on local variables."""
        return {}
