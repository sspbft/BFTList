"""Contains code related to the Replication module."""

# standard
import itertools
import logging
from copy import deepcopy
import time
import os

# local
from modules.algorithm_module import AlgorithmModule
from modules.enums import ReplicationEnums
from modules.constants import (MAXINT, SIGMA,
                               REP_STATE, R_LOG, PEND_REQS, REQ_Q,
                               LAST_REQ, CON_FLAG, VIEW_CHANGE, X_SET,
                               REQUEST, STATUS, SEQUENCE_NO, CLIENT_REQ, PRIM,
                               VIEW, CLIENT, REPLY)
from resolve.enums import Module, Function, MessageType
import conf.config as conf

# globals
logger = logging.getLogger(__name__)


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

    run_forever = True

    def __init__(self, id, resolver, n, f, k):
        """Initializes the module."""
        self.id = id
        self.resolver = resolver
        self.lock = resolver.replication_lock
        self.number_of_nodes = n
        self.number_of_byzantine = f
        self.number_of_clients = k
        self.DEF_STATE = {REP_STATE: [],
                          R_LOG: [],
                          PEND_REQS: [],
                          REQ_Q: [],
                          LAST_REQ: [],
                          CON_FLAG: False,
                          VIEW_CHANGE: False,
                          PRIM: -1}
        self.TEE = deepcopy(self.DEF_STATE)

        self.flush = False
        self.need_flush = False
        self.seq_n = 0
        self.rep = [
            {REP_STATE: [],
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
             VIEW_CHANGE: False,
             PRIM: -1}
            for i in range(n)
        ]

    def run(self):
        """Called whenever the module is launched in a separate thread."""
        sec = os.getenv("INTEGRATION_TEST_SLEEP")
        time.sleep(int(sec) if sec is not None else 0)

        while True:
            # lines 1-3
            self.lock.acquire()
            if (not self.rep[self.id][VIEW_CHANGE] and
                    self.resolver.execute(Module.VIEW_ESTABLISHMENT_MODULE,
                                          Function.ALLOW_SERVICE)):
                view_changed = (self.rep[self.id] != self.TEE and
                                (self.resolver.execute(
                                    Module.VIEW_ESTABLISHMENT_MODULE,
                                    Function.GET_CURRENT_VIEW, self.id) !=
                                    self.rep[self.id][PRIM]))
                self.rep[self.id][VIEW_CHANGE] = view_changed

            self.rep[self.id][PRIM] = self.resolver.execute(
                Module.VIEW_ESTABLISHMENT_MODULE,
                Function.GET_CURRENT_VIEW, self.id)
            prim_id = self.rep[self.id][PRIM]  # alias

            # lines 4-6
            if (self.rep[self.id][VIEW_CHANGE] and prim_id == self.id):
                self.act_as_prim_when_view_changed(prim_id)

            # lines 7-8
            elif(self.rep[self.id][VIEW_CHANGE] and
                 (self.rep[prim_id][VIEW_CHANGE] is False and
                 prim_id == self.rep[prim_id][PRIM])):
                self.act_as_nonprim_when_view_changed(prim_id)

            # lines 9 - 10
            X = self.find_cons_state(self.com_pref_states(
                (3 * self.number_of_byzantine) + 1
            ))
            Y = self.get_ds_state()
            if len(X) == 0 and len(Y) > 0:
                X = Y

            # lines 11 - 14
            self.rep[self.id][CON_FLAG] = (len(X) == 0)
            if (not (self.rep[self.id][CON_FLAG]) and
               (not (self.prefixes(self.rep[self.id][REP_STATE], X)) or
               self.rep[self.id][REP_STATE] == self.DEF_STATE[REP_STATE] or
                    self.delayed())):
                self.rep[self.id][REP_STATE] = deepcopy(X)
            if self.stale_rep() or self.conflict():
                self.flush_local()
                self.rep[self.id] = deepcopy(self.DEF_STATE)
                self.need_flush = True
            if self.flush:
                self.flush_local()

            self.rep[self.id][PEND_REQS].extend(self.known_pend_reqs())
            # line 15 - 25
            if (self.resolver.execute(
                    Module.VIEW_ESTABLISHMENT_MODULE,
                    Function.ALLOW_SERVICE) and (self.need_flush is False)):
                if (self.resolver.execute(
                    Module.PRIMARY_MONITORING_MODULE,
                    Function.NO_VIEW_CHANGE) and
                        self.rep[self.id][VIEW_CHANGE] is False):
                    if prim_id == self.id:
                        # primary processes all pending reqs
                        # TODO re-visit this when Ioannis has answered whether
                        # to use self.get_pend_reqs() instead
                        for req in self.rep[self.id][PEND_REQS]:
                            if self.seq_n < (self.last_exec() +
                               (SIGMA * self.number_of_clients)):
                                self.seq_n += 1
                                req = {
                                    CLIENT_REQ: req[CLIENT_REQ],
                                    VIEW: prim_id,
                                    SEQUENCE_NO: self.seq_n
                                }
                                self.rep[self.id][REQ_Q].append({
                                    REQUEST: req,
                                    STATUS: {
                                        ReplicationEnums.PRE_PREP,
                                        ReplicationEnums.PREP
                                    }
                                })
                    else:
                        # wait for prim or process reqs where 3f+1
                        # agree on seqnum
                        reqs = list(filter(
                            self.reqs_to_prep, self.known_pend_reqs()))
                        for r in reqs:
                            for t in self.rep[self.id][REQ_Q]:
                                # status list will always be [PRE_PREP]
                                if r == t[REQUEST]:
                                    t[STATUS].add(ReplicationEnums.PREP)

                    # consider prepped msgs per request,
                    # if 3f+1 agree then commit
                    for req_status in self.known_reqs({ReplicationEnums.PREP}):
                        req_status[STATUS].add(ReplicationEnums.COMMIT)
                        self.rep[self.id][PEND_REQS].remove(
                                req_status[REQUEST])

                    for req_status in self.known_reqs(
                            {ReplicationEnums.PREP,
                             ReplicationEnums.COMMIT}):
                        x_set = self.committed_set(req_status)
                        if ((len(x_set) >=
                                (3 * self.number_of_byzantine) + 1) and
                                (req_status[REQUEST][SEQUENCE_NO] ==
                                    self.last_exec() + 1)):
                            self.commit({REQUEST: req_status, X_SET: x_set})
            self.lock.release()
            self.send_msg()
            time.sleep(0.1 if os.getenv("INTEGRATION_TEST") else 0.25)

            # Stopping the while loop, used for testing purpose
            if(not self.run_forever):
                break

    def send_msg(self):
        """Broadcasts its own replica_structure to other nodes."""
        for j, in conf.get_other_nodes().keys():
            msg = {
                "type": MessageType.REPLICATION_MESSAGE,
                "sender": self.id,
                "data": {"own_replica_structure": self.rep[self.id]}
            }
            self.resolver.send_to_node(j, msg)

    def receive_rep_msg(self, msg):
        """Logic for receiving a replication message from another node

        The resolver calls this function when a REPLICATION_MESSAGE arrives
        and this function updates the information about the sending node's
        state if allowed.
        """
        if (self.resolver.execute(
                Module.VIEW_ESTABLISHMENT_MODULE,
                Function.ALLOW_SERVICE)):
            j = msg["sender"]                           # id of sender
            rep = msg["data"]["own_replica_structure"]  # rep data
            if (self.resolver.execute(
                    Module.PRIMARY_MONITORING_MODULE,
                    Function.NO_VIEW_CHANGE)):
                self.rep[j] = rep
            else:
                self.rep[j][REP_STATE] = rep[REP_STATE]

    def receive_msg_from_client(self, msg):
        """Logic for receiving a message from a client."""
        # TODO
        pass

    def send_last_exec_req_to_client(self):
        """Replying with last exec req to client."""
        # TODO implement
        pass

    def reqs_to_prep(self, req):
        """Helper method to filter out requests to prepare."""
        if req in self.unassigned_reqs():
            return False
        # TODO req will always be in replica_structure of prim...
        for processor_id, replica_structure in enumerate(self.rep):
            if(processor_id != self.rep[self.id][PRIM]):
                if req in replica_structure[REQ_Q]:
                    return False
        return self.accept_req_preprep(req, self.rep[self.id][PRIM])

    def commit(self, req_status):
        """Commits a request."""
        request = req_status[REQUEST]
        reply = self.apply(request)
        client_id = request[CLIENT_REQ][CLIENT]
        # update last executed request
        self.rep[self.id][LAST_REQ][client_id] = {
            REQUEST: request, REPLY: reply
        }
        # append to rLog
        self.rep[self.id][R_LOG].append(req_status)

        # remove request from pend_reqs and req_q
        self.rep[self.id][PEND_REQS].remove(request)
        req_q = self.rep[self.id][REQ_Q]
        self.rep[self.id][REQ_Q] = \
            [x for x in req_q if x[REQUEST] != request]

    def apply(self, req):
        """Applies a request."""
        logger.info(f"Applying request {req}")
        # TODO implement

    # Macros
    def flush_local(self):
        """Resets all local variables."""
        self.seq_n = 0
        self.rep = [deepcopy(self.DEF_STATE) for i in range(
                                                        self.number_of_nodes)]

    def msg(self, status, processor_j):
        """Returns requests reported to p_i from processor_j with status."""
        request_set = []

        if type(status) is not set:
            raise ValueError("Argument status must be a set")

        for request_pair in self.rep[processor_j][REQ_Q]:
            if status <= request_pair[STATUS]:
                request_set.append(request_pair[REQUEST])
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
        all_replica_states = []
        # Get all replica states
        for replica_structure in self.rep:
            all_replica_states.append(replica_structure[REP_STATE])
        # Find a set of replica states that all are prefixes of each other
        # All possible combinations (of size required_processors) of replica
        # states
        for S in itertools.combinations(
                        all_replica_states, required_processors):
            all_states_are_prefixes = True
            # Check if prefixes for all combinations in the set
            for rep_state_A, rep_state_B in itertools.combinations(S, 2):
                if not self.prefixes(rep_state_A, rep_state_B):
                    # Move on to next combination of replica states
                    all_states_are_prefixes = False
                    break
            # All replica states where prefixes to each other
            if(all_states_are_prefixes):
                return S
        return set()

    def get_ds_state(self):
        """Method description.

        Returns a prefix if suggested by at least 2f+1 and at most 3f+1
        processors, and if there exists another set with the default
        replica state and these two sets adds up to at least 4f+1 processors.
        """
        processors_prefix_X = 0
        processors_in_def_state = 0
        X = self.find_cons_state(self.com_pref_states(
                                2 * self.number_of_byzantine + 1))

        # Find default replica structures and prefixes to/of X
        for replica_structure in self.rep:
            if(replica_structure == self.DEF_STATE):
                processors_in_def_state += 1
                continue
            if self.prefixes(replica_structure[REP_STATE], X):
                processors_prefix_X += 1

        # Checks if the sets are in the correct size span
        if ((2 * self.number_of_byzantine + 1) <= processors_prefix_X <
                (3 * self.number_of_byzantine + 1) and
            ((processors_prefix_X + processors_in_def_state) >=
                (4 * self.number_of_byzantine + 1))):
            return X
        return self.TEE

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

        TODO look into if we should change logic of known_pend_reqs to avoid
        duplicate requests in own pendReqs.
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
            raise ValueError("status arg must be a set")

        request_set = []
        for x in self.rep[self.id][REQ_Q]:
            processor_set = 0
            if x[STATUS] <= status or status <= x[STATUS]:
                for replication_structure in self.rep:
                    for request_pair in replication_structure[REQ_Q]:
                        if(x[REQUEST] == request_pair[REQUEST] and
                           (request_pair[STATUS] <= status or
                           status <= request_pair[STATUS])):
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
        for y in self.msg({ReplicationEnums.PRE_PREP}, prim):
            if y[CLIENT_REQ] == request:
                return True
        return False

    def unassigned_reqs(self):
        """Method description.

        Returns set of pending requests without PRE_PREP msg or
        without having 3f+1 processors reported to have PREP msg
        for the requests.
        """
        request_set = []
        for req in self.rep[self.id][PEND_REQS]:
            if (not self.exists_preprep_msg(
                    req, self.rep[self.id][PRIM]) and
                    req not in list(map(lambda x: x[REQUEST], self.known_reqs(
                        {ReplicationEnums.PREP, ReplicationEnums.COMMIT})))):
                    request_set.append(req)
        return request_set

    def accept_req_preprep(self, request, prim):
        """Method description.

        True if PRE_PREP msg from prim exists and the content is the same for
        3f+1 processors in the same view and sequence number.
        """
        # Processor i knows of the request
        if request in self.known_pend_reqs():
            # The request should be acknowledged by other processors
            for y in self.rep[self.id][REQ_Q]:
                if (y[REQUEST][CLIENT_REQ] == request[CLIENT_REQ] and
                   y[REQUEST][VIEW] == prim and
                   self.exists_preprep_msg(y[REQUEST], prim) and
                   self.last_exec() <= y[REQUEST][SEQUENCE_NO] <=
                        (self.last_exec() + SIGMA * self.number_of_clients)):
                        # A request should not already exist with the same
                        # sequence number or same client request
                        if (self.request_already_exists(y)):
                            # Request y[REQUEST] does not fulfill all
                            # conditions, move on to next request in REQ_Q
                            continue
                        return True
        return False

    def committed_set(self, request):
        """Method description.

        Returns the set of processors that have reported to commit to the
        request or have the request in their executed request log.
        """
        processor_set = set()
        for processor_id, replica_structure in enumerate(self.rep):
            # Checks if the processor has reported to commit the request
            if request in self.msg(ReplicationEnums.COMMIT, processor_id):
                processor_set.add(processor_id)
                continue
            # Checks if the request is in the processors executed request log
            for request_pair in replica_structure[R_LOG]:
                if request == request_pair[REQUEST]:
                    processor_set.add(processor_id)
                    break
        return processor_set

    # Methods added
    def request_already_exists(self, request_p):
        """Checks if request is in REQ_Q or R_LOG.

        Called by accept_req_preprep.
        """
        request = request_p[REQUEST]
        for request_pair in self.rep[self.id][REQ_Q]:
            # If exactly the same, same request with same status.
            # Ignore since it is the request we have as input.
            # If not we will always return True.
            if request_p == request_pair:
                continue
            if (request_pair[REQUEST][CLIENT_REQ] == request[CLIENT_REQ] and
               request_pair[REQUEST][SEQUENCE_NO] == request[SEQUENCE_NO]):
                return True
        for request_pair in self.rep[self.id][R_LOG]:
            if (request_pair[REQUEST][CLIENT_REQ] == request[CLIENT_REQ] and
               request_pair[REQUEST][SEQUENCE_NO] == request[SEQUENCE_NO]):
                return True
        return False

    def prefixes(self, sq_log_A, sq_log_B):
        """Returns true if sequence log A and sequence log B are prefixes."""
        # Go throug sequence log A to see if A is a prefix or B
        for index, item in enumerate(sq_log_A):
            # We have reached the end of sq_log_B and therefore B is a prefix
            # of A
            if len(sq_log_B) <= index:
                return True
            # So far the items in the log are the same
            if item == sq_log_B[index]:
                continue
            # The logs differs and are therefore not prefixes
            else:
                return False

        # Log A has run out of items and is therefore a prefix of B
        return True

    def act_as_prim_when_view_changed(self, prim_id):
        """Actions to perform when a view change has ocurred.

        Processor is the new primary.
        """
        # this node is acting as primary
        processor_ids = set()
        for j, replica_structure in enumerate(self.rep):
            j_prim = self.resolver.execute(
                Module.VIEW_ESTABLISHMENT_MODULE,
                Function.GET_CURRENT_VIEW,
                j
            )
            if (replica_structure[VIEW_CHANGE] and
                    j_prim == self.id):
                processor_ids.add(j)

        if len(processor_ids) >= (4 * self.number_of_byzantine) + 1:
            self.renew_reqs(processor_ids)
            self.find_cons_state(self.com_pref_states(
                (3 * self.number_of_byzantine) + 1
            ))
            # TODO assign REP_STATE and R_LOG to the return val
            # from cons_state when impl.
            self.rep[self.id][VIEW_CHANGE] = False

    def act_as_nonprim_when_view_changed(self, prim_id):
        """Actions to perform when a view change has ocurred.

        Processor is not the new primary.
        """
        processor_ids = []
        for i in range(self.number_of_nodes):
            if (self.resolver.execute(
                    Module.VIEW_ESTABLISHMENT_MODULE,
                    Function.GET_CURRENT_VIEW, i) == prim_id):
                processor_ids.append(i)

        if (len(processor_ids) >=
                (4 * self.number_of_byzantine + 1) and
                self.check_new_v_state(prim_id)):
            self.rep[self.id] = deepcopy(self.rep[prim_id])
            self.rep[self.id][VIEW_CHANGE] = False

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
        # remove requests that does not exist for all
        # processors in processors_set
        seen_reqs = {}
        for processor_id in processors_set:
            for req in self.rep[processor_id][PEND_REQS]:
                if req not in seen_reqs:
                    seen_reqs[req] = 1
                else:
                    seen_reqs[req] = seen_reqs[req] + 1

        # assume no duplicate requests in pendReqs
        seen_reqs = {k: v for (k, v) in seen_reqs.items()
                     if v == len(processors_set)}
        self.rep[self.id][PEND_REQS] = list(seen_reqs.keys())

        # find all reqs that only have pre-prep message, need to create new
        reqs_need_pre_prep = list(filter(
            lambda r: r[STATUS] == {ReplicationEnums.PRE_PREP}),
            self.rep[self.id][REQ_Q]
        )

        for j in processors_set:
            j_req_q = self.rep[j][REQ_Q]
            j_reqs_need_pre_prep = list(filter(
                lambda r: (r[STATUS] == {ReplicationEnums.PRE_PREP} and
                           r in reqs_need_pre_prep)),
                j_req_q)

            # filter out all pre_prep reqs that are not in j's req q
            reqs_need_pre_prep = list(filter(
                lambda r: r in j_reqs_need_pre_prep,
                reqs_need_pre_prep
            ))

        for req in self.rep[self.id][REQ_Q]:
            if req in reqs_need_pre_prep:
                # current view is equal to self.id since we are primary
                req[REQUEST][VIEW] = self.id

    def find_cons_state(self, processors_set):
        """Method description.

        Returns a consolidated replica state based on the processors_set,
        the set should have a common (non-empty) prefix and consistency
        among request and pending queues.
        Produces a dummy request if 3f+1 processor have committed a number
        of request without the existence of the previous request.
        """
        # TODO This should return REP_STATE and R_LOG,
        # which the prim can "adopt"  after a view Change has occured.
        raise NotImplementedError

    def check_new_v_state(self, prim):
        """Method description.

        Check the state proposed by new primary.
        Checks if the PRE_PREP messages are verified by 3f+1 processors and
        that the new state has a correct prefix.
        """
        req_exists_count = {}
        for j, replica_structure in self.rep:
            pre_prep_reqs = list(filter(
                lambda r: r[STATUS] == {ReplicationEnums.PRE_PREP},
                replica_structure[REQ_Q])
            )
            for req_pair in pre_prep_reqs:
                key = {
                    CLIENT_REQ: req_pair[REQUEST][CLIENT_REQ],
                    SEQUENCE_NO: req_pair[REQUEST][SEQUENCE_NO]
                }
                if key in req_exists_count:
                    req_exists_count[key] += 1
                else:
                    req_exists_count[key] = 1

        # find all PRE_PREP msgs with view == prim and check that they exist
        # for 3f + 1 processors
        for req_pair in self.rep[prim][REQ_Q]:
            if req_pair[REQUEST][VIEW] == prim:
                key = {
                    CLIENT_REQ: req_pair[REQUEST][CLIENT_REQ],
                    SEQUENCE_NO: req_pair[REQUEST][SEQUENCE_NO]
                }
                if (key not in req_exists_count or
                        req_exists_count[key] <
                        (3 * self.number_of_byzantine + 1)):
                    return False

        seen_reqs = {}
        for replica_structure in self.rep:
            for req in replica_structure[PEND_REQS]:
                if req not in seen_reqs:
                    seen_reqs[req] = 1
                else:
                    seen_reqs[req] = seen_reqs[req] + 1
        for req in self.rep[prim][PEND_REQS]:
            # check that req exists in >= 3f+1 pendReqs
            if (req not in seen_reqs or
                    seen_reqs[req] < (3 * self.number_of_byzantine + 1)):
                return False

        # TODO implement check that prefix is correct when find_cons_state
        # is implemented

        return True

    # Function to extract data
    def get_data(self):
        """Returns current values on local variables."""
        return {}
