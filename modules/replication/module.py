"""Contains code related to the Replication module."""

# standard
import itertools
import logging
from copy import deepcopy
import time
import os
from typing import List, Tuple

# local
from modules.algorithm_module import AlgorithmModule
from modules.enums import ReplicationEnums, OperationEnums
from modules.constants import (MAXINT, SIGMA, X_SET,
                               REQUEST, STATUS, VIEW_CHANGE)
from resolve.enums import Module, Function, MessageType
import conf.config as conf
from .models.replica_structure import ReplicaStructure
from .models.request import Request
from .models.client_request import ClientRequest
from .models.operation import Operation
import modules.byzantine as byz
from communication.zeromq.rate_limiter import throttle
from metrics.messages import run_method_time
from metrics.state import state_length, client_req_executed

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
    pend_req: [<client_request>]
    req_q : [<request, status t>]
    last_req[K]: (last executed request for each client): [<request, reply>]

    rep[N] (replica structure):
        [<rep_state, r_log, pend_req, req_q, last_req, con_flag, view_change>]
    """

    def __init__(self, id: int, resolver, n, f, k):
        """Initializes the module."""
        self.id = id
        self.resolver = resolver
        self.lock = resolver.replication_lock
        self.number_of_nodes = n
        self.number_of_byzantine = f
        self.number_of_clients = k

        self.flush = False
        self.need_flush = False
        self.rep = [ReplicaStructure(i, k) for i in range(n)] \
            # type: List[ReplicaStructure]
        # Support for non-self-stab
        self.self_stab = os.getenv("NON_SELF_STAB") is None

        if os.getenv("INTEGRATION_TEST") or os.getenv("INJECT_START_STATE"):
            start_state = conf.get_start_state()
            if (start_state is not {} and str(self.id) in start_state and
               "REPLICATION_MODULE" in start_state[str(self.id)]):
                data = start_state[str(self.id)]["REPLICATION_MODULE"]
                rep = data["rep"]
                logger.warning("Injecting start state")
                if rep is not None and len(rep) == n:
                    self.rep = rep
                if byz.is_byzantine():
                    self.byz_rep = deepcopy(rep[self.id])
                    self.byz_client_request = ClientRequest(0, 666, Operation(
                                                "APPEND", 666))
                    self.byz_req = Request(self.byz_client_request, self.id,
                                           666)
                    if byz.get_byz_behavior() == byz.WRONG_CCSP:
                        byz_applied_req = {REQUEST: self.byz_req,
                                           X_SET: {i for i in range(n)}}
                        # Create the byzantine rep_state
                        byz_state = [666]
                        self.byz_rep.set_rep_state(byz_state)
                        self.byz_rep.set_r_log([byz_applied_req])

    def run(self, testing=False):
        """Called whenever the module is launched in a separate thread."""
        sec = os.getenv("INTEGRATION_TEST_SLEEP")
        time.sleep(int(sec) if sec is not None else 0)

        # block until system is ready
        while not testing and not self.resolver.system_running():
            time.sleep(0.1)

        while True:
            # lines 1-3
            self.lock.acquire()
            start_time = time.time()

            # Only execute of self-stablizing
            if self.self_stab:
                view_est_allow_service = self.resolver.execute(
                                            Module.VIEW_ESTABLISHMENT_MODULE,
                                            Function.ALLOW_SERVICE)

                if (not self.rep[self.id].get_view_changed() and
                        view_est_allow_service):
                        # self.resolver.execute(Module.VIEW_ESTABLISHMENT_MODULE,
                                            # Function.ALLOW_SERVICE)):
                    view_changed = (not self.rep[self.id].is_tee() and
                                    (self.resolver.execute(
                                        Module.VIEW_ESTABLISHMENT_MODULE,
                                        Function.GET_CURRENT_VIEW, self.id) !=
                                        self.rep[self.id].get_prim()))
                    self.rep[self.id].set_view_changed(view_changed)
                if view_est_allow_service:

                    self.rep[self.id].set_prim(self.resolver.execute(
                        Module.VIEW_ESTABLISHMENT_MODULE,
                        Function.GET_CURRENT_VIEW, self.id))
                    prim_id = self.rep[self.id].get_prim()  # alias

                    # lines 4-6
                    if (self.rep[self.id].get_view_changed() and
                            prim_id == self.id):
                        self.act_as_prim_when_view_changed(prim_id)

                    # lines 7-8
                    elif(self.rep[self.id].get_view_changed() and
                         (self.rep[prim_id].get_view_changed() is False and
                            prim_id == self.rep[prim_id].get_prim())):
                        self.act_as_nonprim_when_view_changed(prim_id)

                # lines 9 - 10
                # X and Y are tuples (rep_state, r_log, is_default_prefix)
                # -1 in X[0] and Y[0] is used to indicate failure
                X = self.find_cons_state(self.com_pref_states(
                    (3 * self.number_of_byzantine) + 1
                ))
                Y = self.get_ds_state()
                if X[0] == -1 and Y[0] != -1:
                    X = Y
                # lines 11 - 14
                # TODO check if X[1] should be a prefix of r_log?
                # https://bit.ly/2Iu6I0E
                X_rep_state = X[0]
                X_r_log = X[1]
                is_default_prefix = X[2]
                self.rep[self.id].set_con_flag(X_rep_state == -1)
                if (not (self.rep[self.id].get_con_flag()) and
                    (not (self.check_new_X_prefix(self.id,
                                                  X_rep_state,
                                                  is_default_prefix)) or
                     self.rep[self.id].is_def_state() or self.delayed())):
                    # set own rep_state and r_log to consolidated values
                    self.rep[self.id].set_rep_state(deepcopy(X_rep_state))
                    self.rep[self.id].set_r_log(deepcopy(X_r_log))
                # A byzantine node does not care if it is in conflict or stale
                if not byz.is_byzantine():
                    if self.stale_rep() or self.conflict():
                        logger.debug(f"Flushing because stale_rep: " +
                                     f"{self.stale_rep()} or conflict:" +
                                     f" {self.conflict()}")
                        self.flush_local()
                        self.rep[self.id].set_to_tee()
                        self.need_flush = True
                if self.flush:
                    logger.debug(f"Flushing because flush is true")
                    self.flush_local()
                    self.flush = False
            else:
                # These variables are used later
                view_est_allow_service = True
                prim_id = 0

            self.rep[self.id].extend_pend_reqs(self.known_pend_reqs())
            # line 15 - 25
            if view_est_allow_service and self.need_flush is False:
                if (self.resolver.execute(
                    Module.PRIMARY_MONITORING_MODULE,
                    Function.NO_VIEW_CHANGE) and
                        self.rep[self.id].get_view_changed() is False):
                    # prepare requests
                    if (prim_id == self.id and not (byz.is_byzantine() and
                        byz.get_byz_behavior() ==
                            byz.STOP_ASSIGNING_SEQNUMS)):
                        for req in self.unassigned_reqs():
                            if self.rep[self.id].get_seq_num() < \
                                    (self.last_exec() +
                                        (SIGMA * self.number_of_clients)):
                                if byz.is_byzantine():
                                    if (byz.get_byz_behavior() ==
                                            byz.ASSIGN_DIFFERENT_SEQNUMS):
                                        self.byz_rep.set_seq_num(
                                            self.byz_rep.get_seq_num() + 3)
                                        byz_req = Request(
                                            deepcopy(req),
                                            prim_id,
                                            self.byz_rep.get_seq_num()
                                        )
                                        byz_req_pair = {
                                            REQUEST: deepcopy(byz_req),
                                            STATUS: {
                                                ReplicationEnums.PRE_PREP,
                                                ReplicationEnums.PREP
                                            }
                                        }
                                        self.byz_rep.add_to_req_q(byz_req_pair)

                                    elif (byz.get_byz_behavior() ==
                                            byz.SEQNUM_OUT_BOUND):
                                        self.rep[self.id].set_seq_num(
                                            self.rep[self.id].get_seq_num() +
                                            SIGMA * self.number_of_clients + 1)

                                    elif (byz.get_byz_behavior() ==
                                            byz.MODIFY_CLIENT_REQ):
                                        req = ClientRequest(0, 5, Operation(
                                            "APPEND", 5
                                        ))

                                # If not reusing seq_num, increment before
                                # assigning
                                if not (byz.is_byzantine() and
                                        byz.get_byz_behavior() ==
                                        byz.REUSE_SEQNUMS):
                                    self.rep[self.id].inc_seq_num()

                                req = Request(
                                    req,
                                    prim_id,
                                    self.rep[self.id].get_seq_num()
                                )

                                req_pair = {
                                    REQUEST: req,
                                    STATUS: {
                                        ReplicationEnums.PRE_PREP,
                                        ReplicationEnums.PREP
                                    }
                                }
                                self.rep[self.id].add_to_req_q(req_pair)

                    else:
                        # wait for prim or process reqs where 3f+1
                        # agree on seqnum

                        for client_req in self.known_pend_reqs():
                            # Check if any request should get PRE_PREP
                            if self.accept_req_preprep(client_req, prim_id):
                                # Find the actual request from prim
                                for req_pair in self.rep[prim_id].get_req_q():
                                    req = req_pair[REQUEST]
                                    if (req.get_client_request() ==
                                        client_req and req.get_view() ==
                                        prim_id and self.last_exec() <
                                            req.get_seq_num() <=
                                            (self.last_exec() +
                                                SIGMA *
                                                self.number_of_clients)):
                                        # Adding the request with pre_prep
                                        self.rep[self.id].add_to_req_q(
                                            {REQUEST: req,
                                             STATUS: {
                                                 ReplicationEnums.PRE_PREP}
                                             }
                                        )
                                        # No need to search further
                                        break

                        # Find to be PREP:ed
                        for request in self.supported_reqs(
                                    {ReplicationEnums.PRE_PREP}):
                            request_found = False
                            for req_pair in self.rep[self.id].get_req_q():
                                if req_pair[REQUEST] == request:
                                    request_found = True
                                    if req_pair[STATUS] == {
                                            ReplicationEnums.PRE_PREP}:
                                        # Add Prep
                                        req_pair[STATUS].add(
                                            ReplicationEnums.PREP)

                    # Find request to be COMMIT:ed
                    for request in self.supported_reqs(
                            {ReplicationEnums.PREP}):
                        request_found = False
                        for req_pair in self.rep[self.id].get_req_q():
                            if req_pair[REQUEST] == request:
                                request_found = True
                                if req_pair[STATUS] == {
                                        ReplicationEnums.PRE_PREP,
                                        ReplicationEnums.PREP}:
                                    # Add commit
                                    req_pair[STATUS].add(
                                        ReplicationEnums.COMMIT)
                        if not request_found:
                            # Request is not found in own req_q, the request
                            # is supported by 3f + 1 other processors.
                            new_req_pair = {REQUEST: request, STATUS: {
                                ReplicationEnums.PRE_PREP,
                                ReplicationEnums.PREP,
                                ReplicationEnums.COMMIT}}
                            self.rep[self.id].add_to_req_q(new_req_pair)
                        self.rep[self.id].remove_from_pend_reqs(
                            request.get_client_request())

                    # Find all request that should be executed
                    for request in self.supported_reqs(
                        {ReplicationEnums.PREP,
                         ReplicationEnums.COMMIT}):
                        x_set = self.committed_set(request)
                        if ((len(x_set) >=
                                (3 * self.number_of_byzantine) + 1) and
                                (request.get_seq_num() ==
                                    self.last_exec() + 1)):
                            self.commit({REQUEST: request,
                                         X_SET: x_set})

            # Emit run time metric
            run_time = time.time() - start_time
            run_method_time.labels(self.id,
                                   Module.REPLICATION_MODULE).set(
                                       run_time)
            self.lock.release()
            # Stopping the while loop, used for testing purpose
            if(testing):
                break
            self.send_msg()
            throttle()

    def send_msg(self):
        """Broadcasts its own replica_structure to other nodes."""
        for j in conf.get_other_nodes():
            if (byz.is_byzantine() and
               (byz.get_byz_behavior() ==
                    byz.WRONG_CCSP or
                    (byz.get_byz_behavior() ==
                        byz.ASSIGN_DIFFERENT_SEQNUMS and
                        j % 2 == 1))):
                msg = {
                    "type": MessageType.REPLICATION_MESSAGE,
                    "sender": self.id,
                    "data": {"own_replica_structure": self.byz_rep}
                }
            else:
                msg = {
                    "type": MessageType.REPLICATION_MESSAGE,
                    "sender": self.id,
                    "data": {"own_replica_structure": deepcopy(
                                                        self.rep[self.id])}
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
            j = int(msg["sender"])                           # id of sender
            rep = deepcopy(msg["data"]["own_replica_structure"])  # rep data
            if (self.resolver.execute(
                    Module.PRIMARY_MONITORING_MODULE,
                    Function.NO_VIEW_CHANGE)):
                self.rep[j] = deepcopy(rep)
            else:
                self.rep[j].set_rep_state(rep.get_rep_state())

    def receive_msg_from_client(self, msg):
        """Logic for receiving a message from a client."""
        # TODO implement
        pass

    def send_last_exec_req_to_client(self):
        """Replying with last exec req to client."""
        # TODO implement
        pass

    def commit(self, req_pair):
        """Commits a request."""
        request: Request = req_pair[REQUEST]
        reply = self.apply(request)
        client_id = request.get_client_request().get_client_id()
        # update last executed request
        self.rep[self.id].update_last_req(client_id, request, reply)
        # append to rLog
        self.rep[self.id].add_to_r_log(req_pair)

        # remove request from pend_reqs and req_q
        self.rep[self.id].remove_from_pend_reqs(request.get_client_request())
        self.rep[self.id].remove_from_req_q(request)

        # notify state metric that request has been committed
        client_req_executed(request.get_client_request())

    def apply(self, req: Request):
        """Applies a request and returns the resulting state."""
        current_state = self.rep[self.id].get_rep_state()
        operation = req.get_client_request().get_operation()
        new_state = operation.execute(current_state)
        self.rep[self.id].set_rep_state(new_state)
        logger.info(f"Applying request {req}.")

        # state length can only increment by 1 for each APPEND request
        state_length.inc()
        return new_state

    # Macros
    def flush_local(self):
        """Resets all local variables."""
        logger.info("flush_local()")
        self.rep = [ReplicaStructure(i) for i in range(self.number_of_nodes)]
        for r in self.rep:
            r.set_to_tee()

    def msg(self, status, processor_j):
        """Returns requests reported to p_i from processor_j with status."""
        request_set = []

        if type(status) is not set:
            raise ValueError("Argument status must be a set")

        for request_pair in self.rep[processor_j].get_req_q():
            if status <= request_pair[STATUS]:
                request_set.append(request_pair[REQUEST])
        return request_set

    def last_exec(self):
        """Returns last request (highest sequence number) executed.

        Requests are always added with consecutive sequence number, the last
        element in the list is the last executed.
        If no request executed, return -1.
        """
        r_log = self.rep[self.id].get_r_log()
        if r_log:
            return r_log[-1][REQUEST].get_seq_num()
        return -1

    def last_common_exec(self):
        """Method description.

        Returns last request (highest sequence number) executed by at
        least 3f+1 processors. If no such request exist, returns None.
        """
        # Dummy request to start with
        last_common_exec_request = -1
        for replica_structure in self.rep:
            # If R_LOG is empty, ignore that processor
            if(replica_structure.get_r_log() and
               len(replica_structure.get_r_log()) > 0):
                x = replica_structure.get_r_log()[-1]
                # Get the maximal sequence number
                if X_SET not in x:
                    raise ValueError(f"entry in r_log does not have " +
                                     f"x_set key: {x}")
                if (len(x[X_SET]) >=
                   (3 * self.number_of_byzantine + 1)):
                        if (last_common_exec_request == -1 or
                                x[REQUEST].get_seq_num() >
                                last_common_exec_request):
                            last_common_exec_request = x[REQUEST].get_seq_num()
        return last_common_exec_request

    def conflict(self):
        """Returns true if 4f+1 processors has conFlag to true."""
        processors_with_conflicts = 0
        for replica_structure in self.rep:
            if replica_structure.get_con_flag():
                processors_with_conflicts += 1

        if processors_with_conflicts >= (4 * self.number_of_byzantine + 1):
            return True
        return False

    def com_pref_states(self, required_processors) -> Tuple[List, List]:
        """Method description.

        Returns a set of replica states, and corresponding r_logs
        which has the longest prefix at at least required_processors.
        Returns empty if non-existing.
        """
        dct = {}
        # Get all replica states
        for replica_structure in self.rep:
            dct[replica_structure.get_id()] = {
                "REP_STATE": replica_structure.get_rep_state(),
                "R_LOG": replica_structure.get_r_log()
            }
        # Find a set of replica states that all are prefixes of each other
        # All possible combinations (of size required_processors) of replica
        # states
        candidates = []
        for processor_set in itertools.combinations(
                    dct, required_processors):
            all_states_are_prefixes = True
            # Check if prefixes for all combinations in the set of processors
            for id_A, id_B in itertools.combinations(processor_set, 2):
                if not self.are_prefixes(id_A, id_B):
                    # Move on to next combination of replica states
                    all_states_are_prefixes = False
                    break
            # All replica states of the processors were prefixes to each other
            if(all_states_are_prefixes):
                candidates.append(list(processor_set))

        # Found all possible candidates of processors
        # Want to return the ones with the longest prefix of rep_states
        longest_prefix_found = -1
        returning_processors = []
        for processors in candidates:
            states = []
            for id in processors:
                states.append(dct[id]["REP_STATE"])
            prefixes = self.find_prefix(states)
            if prefixes is not None:
                length = len(prefixes)
            else:
                length = -1
            if length > longest_prefix_found:
                longest_prefix_found = length
                returning_processors = processors

        returning_states = []
        returning_r_log = []
        is_default_prefix = False
        # Get all rep_states and r_log of the processors
        for id in returning_processors:
            if self.rep[id].is_def_prefix():
                is_default_prefix = True
            returning_states.append(dct[id]["REP_STATE"])
            returning_r_log.append(dct[id]["R_LOG"])
        return (returning_states, returning_r_log, is_default_prefix)

    def are_prefixes(self, processor_A, processor_B):
        """Checks prefix of whole rep, including default values check.

        A processor with default prefix values is only a prefix of another
        processor with default prefix values.
        """
        if self.rep[processor_A].is_def_prefix():
            # processor_B must also have the default prefix values
            return self.rep[processor_B].is_def_prefix()
        elif self.rep[processor_B].is_def_prefix():
            # Processor A does not have default values but B does
            return False
        else:
            # Return the normal prefix check
            return self.prefixes(self.rep[processor_A].get_rep_state(),
                                 self.rep[processor_B].get_rep_state())

    def check_new_X_prefix(self, id, X_rep, is_default_prefix):
        """Checks the new prefix rep_state (X_rep) proposed."""
        if self.rep[id].is_def_prefix():
            return is_default_prefix
        elif is_default_prefix:
            # Own rep is not default value
            return False
        else:
            return self.prefixes(self.rep[id].get_rep_state(), X_rep)

    def get_ds_state(self) -> Tuple[List, List]:
        """Method description.

        Returns a prefix if suggested by at least 2f+1 and at most 3f+1
        processors, and if there exists another set with the default
        replica state and these two sets adds up to at least 4f+1 processors.
        """
        processors_prefix_X = 0
        processors_in_def_state = 0
        X = self.find_cons_state(self.com_pref_states(
                                2 * self.number_of_byzantine + 1))
        if X[0] == -1:
            return X
        is_default_prefix = X[2]
        # Find default replica structures and prefixes to/of X
        for replica_structure in self.rep:
            if(replica_structure.is_rep_state_default()):
                processors_in_def_state += 1
                continue
            if self.check_new_X_prefix(replica_structure.get_id(),
                                       X[0],
                                       is_default_prefix):
                processors_prefix_X += 1

        # Checks if the sets are in the correct size span
        if ((2 * self.number_of_byzantine + 1) <= processors_prefix_X <
                (3 * self.number_of_byzantine + 1) and
            ((processors_prefix_X + processors_in_def_state) >=
                (4 * self.number_of_byzantine + 1))):
            return X
        return (-1, [], False)

    def double(self):
        """Method description.

        Returns true if request queue contains two copies of a client request
        with different sequence numbers or views.
        """
        # Create all possible 2-combinations of the requests
        for request_pair1, request_pair2 in itertools.combinations(
                self.rep[self.id].get_req_q(), 2):
            if(request_pair1[REQUEST].get_client_request() ==
                    request_pair2[REQUEST].get_client_request() and
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
        for request in self.rep[self.id].get_req_q():
            processors_supporting = 0
            my_request = request[REQUEST]
            client_request = my_request.get_client_request()
            # get replica states of all other processors
            for replica_structure in self.rep:
                # for all request in their request queue
                for req_pair in replica_structure.get_req_q():
                    if(client_request ==
                            req_pair[REQUEST].get_client_request()):
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
        for request_pair in self.rep[self.id].get_r_log():
            if(len(request_pair[X_SET]) < (3 * self.number_of_byzantine + 1)):
                x_set_less = True
        # NOTE that self.unsup_req was originally called as well. Removed
        # during integration testing of rep mod and discussion at meeting 26/2
        return (self.stale_req_seqn() or self.double() or x_set_less)

    def known_pend_reqs(self):
        """Method description.

        Returns the set of requests in request queue and in the message queue
        of 3f+1 other processors.
        """
        request_count = {}

        for rs in self.rep:
            for req in rs.get_pend_reqs():
                if req in request_count:
                    request_count[req] += 1
                else:
                    request_count[req] = 1

        known_reqs = {k: v for (k, v) in request_count.items() if v >= (
                        3 * self.number_of_byzantine + 1)}
        return list(known_reqs.keys())

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
        for req_pair in self.rep[self.id].get_req_q():
            processor_set = 0
            if status <= req_pair[STATUS]:
                for replication_structure in self.rep:
                    for request_pair in replication_structure.get_req_q():
                        if(req_pair[REQUEST] == request_pair[REQUEST] and
                           status <= request_pair[STATUS]):
                            processor_set += 1
            if processor_set >= (3 * self.number_of_byzantine + 1):
                request_set.append(req_pair)
        return request_set

    def supported_reqs(self, status):
        """Returns all reqs that exist in the r_log

        or req_q with status "status" of 3f+1 processors.
        """
        known_reqs = {}

        for replica_structure in self.rep:
            for req_pair in replica_structure.get_req_q():
                if status <= req_pair[STATUS]:
                    if req_pair[REQUEST] in known_reqs:
                        known_reqs[req_pair[REQUEST]] += 1
                    else:
                        known_reqs[req_pair[REQUEST]] = 1

            for applied_req in replica_structure.get_r_log():
                    if applied_req[REQUEST] in known_reqs:
                        known_reqs[applied_req[REQUEST]] += 1
                    else:
                        known_reqs[applied_req[REQUEST]] = 1

        known_reqs = {k: v for (k, v) in known_reqs.items()
                      if v >= (3 * self.number_of_byzantine + 1)}
        # Filter out all request that processor_i has already applied
        for applied_req in self.rep[self.id].get_r_log():
            if applied_req[REQUEST] in known_reqs:
                del known_reqs[applied_req[REQUEST]]
        return list(known_reqs.keys())

    def delayed(self):
        """Method description.

        Returns true if the last executed request is smaller than last common
        executed request plus
        3*cardinality size of the clients set*defined integer constant(3Ksigma)
        """
        return (self.last_exec() <
                (self.last_common_exec() - 3 * self.number_of_clients * SIGMA))

    def exists_preprep_msg(self, request: ClientRequest, prim: int):
        """Method description.

        Returns true if there exists a PRE_PREP msg from the primary
        for the request.
        """
        for y in self.msg({ReplicationEnums.PRE_PREP}, prim):
            if y.get_client_request() == request:
                return True
        return False

    def unassigned_reqs(self):
        """Method description.

        Returns set of pending requests without PRE_PREP msg or
        without having 3f+1 processors reported to have PREP msg
        for the requests.
        """
        request_set = []
        for req in self.rep[self.id].get_pend_reqs():
            if (not self.exists_preprep_msg(
                    req, self.rep[self.id].get_prim()) and
                    req not in list(map(lambda x:
                                        x[REQUEST].get_client_request(),
                                        self.known_reqs(
                                            {ReplicationEnums.PREP,
                                             ReplicationEnums.COMMIT}))
                                    )):
                    request_set.append(req)
        return request_set

    def accept_req_preprep(self, request: ClientRequest, prim: int):
        """Method description.

        True if PRE_PREP msg from prim exists and the content is the same for
        3f+1 processors in the same view and sequence number.
        """
        # Processor i knows of the request and there exists a pre_prep_message
        if (request in self.known_pend_reqs() and
           self.exists_preprep_msg(request, prim)):
            # The request should be acknowledged by other processors
            for req_pair in self.rep[prim].get_req_q():
                if (req_pair[REQUEST].get_client_request() == request and
                   req_pair[REQUEST].get_view() == prim and
                   self.last_exec() < req_pair[REQUEST].get_seq_num() <=
                        (self.last_exec() + SIGMA * self.number_of_clients)):
                        # A request should not already exist with the same
                        # sequence number or same client request
                        if (self.request_already_exists(req_pair[REQUEST])):
                            # Request y[REQUEST] does not fulfill all
                            # conditions, move on to next request in REQ_Q
                            continue
                        return True
        for applied_req in self.rep[prim].get_r_log():
            if (applied_req[REQUEST].get_client_request() == request and
                applied_req[REQUEST].get_view() == prim and
                self.last_exec() < applied_req[REQUEST].get_seq_num() <=
                    (self.last_exec() + SIGMA * self.number_of_clients)):
                # A request should not already exist with the same
                # sequence number or same client request
                if (self.request_already_exists(applied_req[REQUEST])):
                    # Request y[REQUEST] does not fulfill all
                    # conditions, move on to next request in REQ_Q
                    continue
                return True
        return False

    def prep_request_already_exists(self, req: Request):
        """Method description.

        True if a Prep msg already exists for the request.
        """
        # Checks if the request already has as a prep_message or a
        # commit message
        for request_pair in self.rep[self.id].get_req_q():
            # We have found the pair
            if (request_pair[REQUEST].get_client_request() ==
                req.get_client_request() and
               request_pair[REQUEST].get_seq_num() == req.get_seq_num()):
                # If the request has a status that is something else than just
                # PRE_PREP, the request already exists with a PREP/COMMIT
                if(request_pair[STATUS] != {ReplicationEnums.PRE_PREP}):
                    return True
        # Checks if the request already has been executed (r_log)
        for request_pair in self.rep[self.id].get_r_log():
            if (request_pair[REQUEST].get_client_request() ==
                req.get_client_request() and
               request_pair[REQUEST].get_seq_num() == req.get_seq_num()):
                return True
        return False

    def committed_set(self, request: Request):
        """Method description.

        Returns the set of processors that have reported to commit to the
        request or have the request in their executed request log.
        """
        processor_set = set()
        for replica_structure in self.rep:
            id = replica_structure.get_id()
            # Checks if the processor has reported to commit the request
            if request in self.msg({ReplicationEnums.COMMIT}, id):
                processor_set.add(id)
                continue
            # Checks if the request is in the processors executed request log
            for request_pair in replica_structure.get_r_log():
                if request == request_pair[REQUEST]:
                    processor_set.add(id)
                    break
        return processor_set

    # Methods added
    def request_already_exists(self, req: Request):
        """Checks if request is in REQ_Q or R_LOG of current processor.

        Called by accept_req_preprep.
        """
        # Checks if the request is pending in req_q
        for request_pair in self.rep[self.id].get_req_q():
            if (request_pair[REQUEST].get_client_request() ==
                req.get_client_request() and
               request_pair[REQUEST].get_seq_num() == req.get_seq_num() and
               request_pair[REQUEST].get_view() == req.get_view()):
                return True
        # Checks if the request already has been committed
        for request_pair in self.rep[self.id].get_r_log():
            if (request_pair[REQUEST].get_client_request() ==
                req.get_client_request() and
               request_pair[REQUEST].get_seq_num() == req.get_seq_num() and
               request_pair[REQUEST].get_view() == req.get_view()):
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

    def is_prefix_of(self, sq_log_A, sq_log_B):
        """Returns True if sq_log_A is a prefix of sq_log_B."""
        if len(sq_log_A) > len(sq_log_B):
            return False

        # Check entries in A to see that they match entries in B
        for index, item in enumerate(sq_log_A):
            if item == sq_log_B[index]:
                continue
            else:
                return False
        return True

    def act_as_prim_when_view_changed(self, prim_id):
        """Actions to perform when a view change has ocurred.

        Processor is the new primary.
        """
        # this node is acting as primary
        processor_ids = set()
        for replica_structure in self.rep:
            j = replica_structure.get_id()
            j_prim = self.resolver.execute(
                Module.VIEW_ESTABLISHMENT_MODULE,
                Function.GET_CURRENT_VIEW,
                j
            )
            if (replica_structure.get_view_changed() and
                    j_prim == self.id):
                processor_ids.add(j)

        if len(processor_ids) >= (4 * self.number_of_byzantine) + 1:
            # Update our sequence number to the most recent one.
            potential_seq = -1
            # Find max sequence number of requests that has not yet been
            # committed, but should not receive new sequence numbers.
            for request_pair in self.rep[self.id].get_req_q():
                if request_pair[STATUS] == {ReplicationEnums.PRE_PREP,
                                            ReplicationEnums.PREP}:
                    potential_seq = max(potential_seq,
                                        request_pair[REQUEST].get_seq_num())
            # If no potential sequence number,
            # (all assigned request has been committed)
            # then add last executed sequence number
            new_seq = max(self.last_exec(), potential_seq)
            try:
                self.rep[self.id].set_seq_num(new_seq)
            except TypeError as e:
                logger.error(f"Got error {e} when setting new seq_num. " +
                             f"self.rep[self.id] = {str(self.rep[self.id])}")
            last_seq_num = self.last_exec()
            while new_seq > last_seq_num:
                # check if missing requests are in request queue
                last_seq_num += 1
                if not self.req_with_seq_num_in_req_q(last_seq_num):
                    # add dummy request to req_q
                    req_pair = self.produce_dummy_req(last_seq_num)
                    self.rep[self.id].add_to_req_q(req_pair)

            self.renew_reqs(processor_ids)
            # X is a tuple (rep_state, r_log)
            X = self.find_cons_state(self.com_pref_states(
                (3 * self.number_of_byzantine) + 1
            ))

            # check if something went wrong
            if X[0] == -1:
                self.rep[self.id].set_to_tee()
            # update values accordingly
            else:
                self.rep[self.id].set_rep_state(X[0])
                self.rep[self.id].set_r_log(X[1])
                self.rep[self.id].set_view_changed(False)

    def req_with_seq_num_in_req_q(self, seq_num):
        """Checks if a request with a certain seq num exists in req queue."""
        for r in self.rep[self.id].get_req_q():
            if r[REQUEST].get_seq_num() == seq_num:
                return True
        return False

    def produce_dummy_req(self, seq_num):
        """Produces a NO-OP request with the given seq num."""
        dummy_request = Request(
            ClientRequest(-1, None, Operation(
                OperationEnums.NO_OP
            )),
            self.id, seq_num)
        return {
            REQUEST: dummy_request,
            STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PRE_PREP}
        }

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
            self.rep[self.id].set_replica_structure(self.rep[prim_id])
            self.rep[self.id].set_view_changed(False)

    # Interface functions
    def rep_need_flush(self):
        """Returns True if Replication modules demands a flush."""
        return self.need_flush

    def get_pend_reqs(self):
        """Method description.

        Returns requests in pending request queue that has not been
        assigned a sequence number and appears in the request queue
        of other processors.
        """
        if not self.rep[self.id].get_view_changed():
            intersection_set = set(self.known_pend_reqs()).intersection(
                                            set(self.unassigned_reqs()))
            return(list(intersection_set))
            # return(self.known_pend_reqs().intersection(self.unassigned_reqs()))
        else:
            return(VIEW_CHANGE)

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
        the processors in processor_set.
        """
        # remove requests that does not exist for all
        # processors in processors_set
        seen_reqs = {}
        for processor_id in processors_set:
            for req in self.rep[processor_id].get_pend_reqs():
                if req not in seen_reqs:
                    seen_reqs[req] = 1
                else:
                    seen_reqs[req] = seen_reqs[req] + 1

        # assume no duplicate requests in pendReqs
        seen_reqs = {k: v for (k, v) in seen_reqs.items()
                     if v == len(processors_set)}
        self.rep[self.id].set_pend_reqs(list(seen_reqs.keys()))

        # find all reqs that only have pre-prep message, need to create new
        reqs_need_pre_prep = list(filter(
            lambda r: r[STATUS] == {ReplicationEnums.PRE_PREP},
            self.rep[self.id].get_req_q())
        )

        for j in processors_set:
            j_req_q = self.rep[j].get_req_q()
            j_reqs_need_pre_prep = list(filter(
                lambda r: (r[STATUS] == {ReplicationEnums.PRE_PREP} and
                           r in reqs_need_pre_prep),
                j_req_q))

            # filter out all pre_prep reqs that are not in j's req q
            reqs_need_pre_prep = list(filter(
                lambda r: r in j_reqs_need_pre_prep,
                reqs_need_pre_prep
            ))

        for req in self.rep[self.id].get_req_q():
            if req in reqs_need_pre_prep:
                # current view is equal to self.id since we are primary
                req[REQUEST].set_view(self.id)

                # Increment sequence number and assign
                self.rep[self.id].inc_seq_num()
                req[REQUEST].set_seq_num(self.rep[self.id].get_seq_num())
                # Add PREP since node is primary and do not need to validate
                # PRE_PREP - message
                req[STATUS].add(ReplicationEnums.PREP)

    def find_cons_state(self, processors_tuple) -> Tuple[List, List]:
        """Method description.

        Returns a consolidated replica state based on the processors_states,
        the set should have a common (non-empty) prefix and consistency
        among request and pending queues.
        Produces a dummy request if 3f+1 processor have committed a number
        of request without the existence of the previous request.

        NOTE that this assumes that elements in rep_state have a corresponding
        r_log entry at this processor.
        NOTE that returning (-1, *) means that something went wrong.
        """
        processors_states = processors_tuple[0]
        processors_r_log = processors_tuple[1]
        is_default_prefix = processors_tuple[2]

        if len(processors_states) == 0:
            logger.debug("Unable to find con_state because states =[]")
            return (-1, [], False)
        prefix_state = self.find_prefix(processors_states)
        if prefix_state is None:
            logger.debug("Unable to find con_state because prefix =[]")
            return (-1, [], False)
        # Find corresponding r_log
        r_log = self.get_corresponding_r_log(processors_r_log, prefix_state)
        # Check if inconsistency between r_log and rep_state
        if r_log == [] and len(prefix_state) > 0:
            logger.debug("Unable to find con_state because r_log =[]")
            return (-1, [], False)
        return (prefix_state, r_log, is_default_prefix)

    def get_corresponding_r_log(self, processors_r_log, prefix_state):
        """Returns the corresponding r_log to the prefix_state.

        Processors_r_log is a list of r_logs corresponding to the processors
        which rep_state has prefix_state as prefix.
        """
        for single_r_log in processors_r_log:
            for entries in itertools.combinations(
                    single_r_log, len(prefix_state)):
                # execute all reqs in this combination
                state = []
                for e in entries:
                    op = e[REQUEST].get_client_request().get_operation()
                    if type(op) is not Operation:
                        raise ValueError(f"Operation {op} in r_log entry is \
                                            not of type Operation")
                    state = op.execute(state)
                if state == prefix_state:
                    # found correct r_log entries
                    # entries is tuple -> convert to list
                    return list(entries)
        return []

    def find_prefix(self, rep_states: List):
        """Finds the prefix of a list of replica states."""
        prefix = None

        # find shortest rep state
        shortest = rep_states[0]
        for i in range(1, len(rep_states)):
            if len(rep_states[i]) < len(shortest):
                shortest = rep_states[i]

        if len(shortest) == 0:
            return []

        # check for same value in all rep_states at a given index to find
        # prefix
        for i in range(len(shortest)):
            starting_val = shortest[i]
            for r in rep_states:
                if r[i] != starting_val:
                    return prefix
            if prefix is None:
                prefix = []
            prefix.append(starting_val)

        return prefix

    def check_new_v_state(self, prim):
        """Method description.

        Check the state proposed by new primary.
        Checks if the PRE_PREP messages are verified by 3f+1 processors and
        that the new state has a correct prefix.
        """
        req_exists_count = {}
        for replica_structure in self.rep:
            pre_prep_reqs = list(filter(
                lambda r: r[STATUS] == {ReplicationEnums.PRE_PREP},
                replica_structure.get_req_q())
            )
            for req_pair in pre_prep_reqs:
                key = req_pair[REQUEST].get_client_request()
                if key in req_exists_count:
                    req_exists_count[key] += 1
                else:
                    req_exists_count[key] = 1
        # find all PRE_PREP msgs with view == prim and check that they exist
        # for 3f + 1 processors
        for req_pair in self.rep[prim].get_req_q():
            if req_pair[REQUEST].get_view() == prim:
                key = req_pair[REQUEST].get_client_request()
                # add dummy requests to req_q to avoid halting
                if key.is_dummy():
                    dummy_seq_num = req_pair[REQUEST].get_seq_num()
                    # make sure dummy seq num does not exist for other req
                    # in req q
                    for r in self.rep[prim].get_req_q():
                        if (r[REQUEST].get_client_request() != key and
                           r[REQUEST].get_seq_num() == dummy_seq_num):
                            return False
                    continue
                elif (key not in req_exists_count or
                      req_exists_count[key] <
                      (3 * self.number_of_byzantine + 1)):  # and
                    if self.accept_req_preprep(key, prim):
                        # A request that is PRE_PREP:ed by the primary but
                        # didn't have a supported PRE_PREP from last view
                        continue
                    else:
                        # The request was not supported and should not be
                        # accepted
                        return False

        seen_reqs = {}
        for replica_structure in self.rep:
            for req in replica_structure.get_pend_reqs():
                if req not in seen_reqs:
                    seen_reqs[req] = 1
                else:
                    seen_reqs[req] = seen_reqs[req] + 1
        for req in self.rep[prim].get_pend_reqs():
            # check that req exists in >= 3f+1 pendReqs
            if (req not in seen_reqs or
                    seen_reqs[req] < (3 * self.number_of_byzantine + 1)):
                return False

        return self.check_new_state_and_r_log(prim)

    def check_new_state_and_r_log(self, prim) -> bool:
        """Checks the state and r_log proposed by the new primary."""
        # check that new state is prefix to 3f+1 processors
        count = 0
        prim_state = self.rep[prim].get_rep_state()
        for rs in self.rep:
            rep_state = rs.get_rep_state()
            if self.is_prefix_of(prim_state, rep_state):
                count += 1
        if count < (3 * self.number_of_byzantine + 1):
            return False

        # check r_log
        state = []
        for e in self.rep[prim].get_r_log():
            op = e[REQUEST].get_client_request().get_operation()
            state = op.execute(state)

        return state == self.rep[prim].get_rep_state()

    def get_unknown_supported_prep(self):
        """Returns all requests that are supported by 3f+1 processor

        but are unknown to processor i, meaning it does not exists in req_q.
        """
        reqs_count = {}
        for rs in self.rep:
            # No need to look through more than n - 3f since unknown
            # requests will then not be supported
            # (if not found before, then the request can't have 3f+1 nodes
            # supporting it)
            for req_pairs in rs.get_req_q():
                if {ReplicationEnums.PREP} <= req_pairs[STATUS]:
                    # The request has PREP_message
                    for rp in self.rep[self.id].get_req_q():
                        if rp[REQUEST] != req_pairs[REQUEST]:
                            # Request does not exist in own req_q, count i
                            if req_pairs[REQUEST] in reqs_count:
                                reqs_count[req_pairs[REQUEST]] += 1
                            else:
                                reqs_count[req_pairs[REQUEST]] = 1
        # Get all supported requests
        supported_reqs = {k: v for (k, v) in reqs_count.items() if v >= (
                                    3 * self.number_of_byzantine + 1)}
        return list(supported_reqs.keys())

    # Function to extract data
    def get_data(self):
        """Returns current values on local variables."""
        rep = self.rep[self.id]
        return {
            "id": self.id,
            "rep_state": rep.get_rep_state(),
            "pend_reqs": rep.get_pend_reqs(),
            # get status name instead of int
            "req_q": list(map(lambda x: {
                        REQUEST: x[REQUEST],
                        STATUS: set(map(lambda y: y.name, x[STATUS]))
                    }, rep.get_req_q())),
            "last_req": rep.get_last_req(),
            "seq_num": rep.get_seq_num(),
            "con_flag": rep.get_con_flag(),
            "view_changed": rep.get_view_changed(),
            "r_log": rep.get_r_log(),
            "prim": rep.get_prim()
        }

    def inject_client_req(self, req: ClientRequest):
        """Injects a client request to pend_reqs."""
        self.rep[self.id].extend_pend_reqs([req])
        return self.rep[self.id].get_pend_reqs()
