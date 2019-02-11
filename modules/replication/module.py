"""Contains code related to the Replication module."""

import time
import itertools
from modules.algorithm_module import AlgorithmModule
# from modules.enums import ReplicationEnums
from modules.constants import (MAXINT, SIGMA,
                               REP_STATE, R_LOG, PEND_REQS, REQ_Q,
                               LAST_REQ, CON_FLAG, VIEW_CHANGE, X_SET,
                               REQUEST, STATUS, SEQUENCE_NO, CLIENT_REQ)
# , X_SET, REPLY
from copy import deepcopy


class ReplicationModule(AlgorithmModule):
    """Models the Replication module.

    Structure of variables:
    client_request (request by client): <client c, timestamp t, operation o>
    request (accepted request): < request client_request, view v,
                                                    sequence number seq_n>
    rep_state = UNDEFINED
    r_log (x_set is the set that claim to have executed/comitted request):
        [<request, x_set>]
    pend_req: [<request>]
    req_q : [<request, status t>]
    last_req[K]: (last executed request for each client): [<request, reply>]

    rep[N] (replica structure):
        [<rep_state, r_log, pend_req, req_q, last_req, con_flag, view_change>]
    """

    def __init__(self, id, resolver, n, f, k):
        """Initializes the module."""
        self.id = id
        self.resolver = resolver
        self.number_of_nodes = n
        self.number_of_byzantine = f
        self.number_of_clients = k
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
        self.prim = -1

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
        request_set = []
        for request_pair in self.rep[processor_j].get(REQ_Q):
            if request_pair.get(STATUS) == status:
                request_set.append(request_pair.get(REQUEST))
        return request_set

    def last_exec(self):
        """Returns last request (highest sequence number) executed.

        Requests are always added with consecutive sequence number, the last
        element in the list is the last executed.
        If no request executed, return None.
        """
        if(self.rep[self.id][R_LOG]):
            return self.rep[self.id][R_LOG][-1][REQUEST][SEQUENCE_NO]
        return None

    def last_common_exec(self):
        """Method description.

        Returns last request (highest sequence number) executed by at
        least 3f+1 processors. If no such request exist, returns None.
        """
        # Dummy request to start with
        last_common_exec_request = None
        for replica_structure in self.rep:
            # If R_LOG is empty, ignore that processor
            if(replica_structure[R_LOG]):
                # Get last excecuted request done by this processor
                x = replica_structure[R_LOG][-1]
                # Get the maximal sequence number
                if (len(x[X_SET]) >=
                   (3 * self.number_of_byzantine + 1)):
                        if (last_common_exec_request is None):
                            last_common_exec_request = deepcopy(
                                x[REQUEST][SEQUENCE_NO])
                        elif (x[REQUEST][SEQUENCE_NO] >
                              last_common_exec_request):
                                last_common_exec_request = deepcopy(
                                    x[REQUEST][SEQUENCE_NO])
        return last_common_exec_request

    def conflict(self):
        """Returns true if 4f+1 processors has conFlag to true."""
        processors_with_conflicts = 0
        for replica_structure in self.rep:
            if(replica_structure[CON_FLAG]):
                processors_with_conflicts += 1

        if processors_with_conflicts >= (4 * self.number_of_byzantine + 1):
            return True
        return False

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

        Returns true if request queue contains two copies of a client request
        with different sequence numbers or views.
        """
        # Create all possible 2-combinations of the requests
        for request_pair1, request_pair2 in itertools.combinations(
                                                self.rep[self.id][REQ_Q], 2):
            if(request_pair1[REQUEST][CLIENT_REQ] ==
                request_pair2[REQUEST][CLIENT_REQ] and
                # the sequence number or view number is different
                    request_pair1[REQUEST] != request_pair2[REQUEST]):
                return True
        return False

    def stale_req_seqn(self):
        """Returns true if the sequence number has reached its limit."""
        return((self.last_exec() + self.number_of_clients * SIGMA) >
               MAXINT)

    def unsup_req(self):
        """Method description.

        Returns true if a request exists in request queue less than
        2f+1 times (the request is unsupported).
        """
        for request in self.rep[self.id][REQ_Q]:
            processors_supporting = 0
            my_request = request[REQUEST]
            client_request = my_request[CLIENT_REQ]
            # get replica states of all other processors
            for replica_state in self.rep:
                # for all request in their request queue
                for req in replica_state[REQ_Q]:
                    if(client_request == req[REQUEST][CLIENT_REQ]):
                        processors_supporting += 1
            if(processors_supporting < (2 * self.number_of_byzantine + 1)):
                return True
        return False

    def stale_rep(self):
        """Returns true if

        double(), unsup_req, stale_req_seqn is true or if there is a request
        that does not have the support of at least 3f + 1 processors.
        """
        x_set_less = False
        for request_pair in self.rep[self.id][R_LOG]:
            if(len(request_pair[X_SET]) <= (3 * self.number_of_byzantine + 1)):
                x_set_less = True
        return (self.stale_req_seqn() or self.unsup_req() or self.double() or
                x_set_less)

    def known_pend_reqs(self):
        """Method description.

        Returns the set of requests in request queue and in the message queue
        of 3f+1 other processors.
        """
        request_set = []
        for x in self.rep[self.id][PEND_REQS]:
            processor_set = 0
            for replica_structure in self.rep:
                if x in replica_structure[PEND_REQS]:
                    processor_set += 1
                else:
                    # Avoid searching this queue if already found in pending
                    # requests
                    for request_pair in replica_structure[REQ_Q]:
                        if x == request_pair[REQUEST]:
                            processor_set += 1

            if(processor_set >= (3 * self.number_of_byzantine + 1)):
                request_set.append(x)
        return request_set

    def known_reqs(self, status):
        """Method description.

        Returns the set of requests in request queue and in the request queue
        of 3f+1 other processors with status.
        Status is a set of statuses
        """
        # If the input is only one element, and not as a set, convert to a set
        if type(status) is not set:
            status = {status}

        request_set = []
        for x in self.rep[self.id][REQ_Q]:
            processor_set = 0
            if x[STATUS] in status:
                for replication_structure in self.rep:
                    for request_pair in replication_structure[REQ_Q]:
                        if(x[REQUEST] == request_pair[REQUEST] and
                           request_pair[STATUS] in status):
                            processor_set += 1
            if processor_set >= (3 * self.number_of_byzantine + 1):
                request_set.append(x)
        return request_set

    def delayed(self):
        """Method description.

        Returns true if the last executed request is smaller than last common
        executed request plus
        3*cardinality size of the clients set*defined integer constant(3Ksigma)
        """
        return (self.last_exec() <
                (self.last_common_exec() - 3 * self.number_of_clients * SIGMA))

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
