import unittest
from unittest.mock import Mock, MagicMock, call
import sys
from resolve.resolver import Resolver
from modules.replication.module import ReplicationModule
from resolve.enums import Function, Module
from modules.enums import ReplicationEnums
from modules.constants import (REP_STATE, R_LOG, PEND_REQS, REQ_Q,
                               LAST_REQ, CON_FLAG, VIEW_CHANGE,
                               REQUEST, SEQUENCE_NO, STATUS, VIEW, X_SET, CLIENT_REQ,
                               SIGMA) # REPLY

class TestReplicationModule(unittest.TestCase):

    def setUp(self):
        self.resolver = Resolver()
        self.dummyRequest1 = {CLIENT_REQ: {1}, VIEW: 1, SEQUENCE_NO: 1}
        self.dummyRequest2 = {CLIENT_REQ: {2}, VIEW: 1, SEQUENCE_NO: 2}
    
    def test_resolver_can_be_initialized(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        self.assertIsNotNone(replication)

    # Macros

    def test_flush_local(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        replication.flush_local()
        # The local variables should be the default values
        rep_default = [{REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
             VIEW_CHANGE: False},
             {REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
             VIEW_CHANGE: False}]
        self.assertEqual(replication.seq_n, 0)
        self.assertEqual(replication.rep, rep_default)

    def test_msg(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        replication.rep[1][REQ_Q] = [
                {REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP},
                {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP}]

        self.assertEqual(replication.msg(ReplicationEnums.PRE_PREP, 1), [self.dummyRequest1])
        self.assertEqual(replication.msg(ReplicationEnums.PREP, 1), [self.dummyRequest2])
        self.assertEqual(replication.msg(ReplicationEnums.COMMIT, 1), [])

    def test_last_execution(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        # The last executed is dummyRequest 2 with sequence number 2
        replication.rep[replication.id][R_LOG] = [{REQUEST: self.dummyRequest1, X_SET: {5}},
                                  {REQUEST: self.dummyRequest2, X_SET: {5}}]

        self.assertEqual(replication.last_exec(), 2)
        # There is no executed requests
        replication.rep[replication.id][R_LOG] = []

        self.assertIsNone(replication.last_exec())
        

    def test_last_common_execution(self):
        # 4 nodes, 1 byzantine
        replication = ReplicationModule(0, self.resolver, 5, 1, 1)

        # The last common executed request has sequence number 2
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [{REQUEST: self.dummyRequest1, X_SET:{}},
                    {REQUEST: self.dummyRequest2, X_SET:{0,1,2,3,4,5}}],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(5)]

        self.assertEqual(replication.last_common_exec(), 2)

        # There is no common last executed request, 3 nodes have
        # request 1 and 2 nodes have not executed anything.
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [{REQUEST: self.dummyRequest1, X_SET:{}}],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(2)] + [{
                REP_STATE: {},
                R_LOG: [],
                PEND_REQS: [],
                REQ_Q: [],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(3,5)]

        self.assertIsNone(replication.last_common_exec())

        # There is no common last executed request, 3 nodes have request 1 and 2 nodes request 2
        # This case should not happen, the last 2 nodes should not be able to add request 2 without
        # seeing request 2. But it checks the logic of the function.
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [{REQUEST: self.dummyRequest1, X_SET:{0,1,2}}],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(2)] + [{
                REP_STATE: {},
                R_LOG: [{REQUEST: self.dummyRequest2, X_SET:{3,4,5}}],
                PEND_REQS: [],
                REQ_Q: [],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(3,5)]

        self.assertIsNone(replication.last_common_exec())

        # The common last executed request is request 1 (sequence number 1)
        # 3 nodes have only request 1 and 2 nodes request 1 and request 2
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [{REQUEST: self.dummyRequest1, X_SET:{0,1,2,3,4,5}}],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(2)] + [{
                REP_STATE: {},
                R_LOG: [{REQUEST: self.dummyRequest1, X_SET:{0,1,2,3,4,5}},
                        {REQUEST: self.dummyRequest2, X_SET:{3,4,5}}],
                PEND_REQS: [],
                REQ_Q: [],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(3,5)]

        self.assertEqual(replication.last_common_exec(), 1)

    def test_conflict(self):
        # 6 nodes 1 byzantine
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)

        # All but one node have their conflict flag to True
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: True,
            VIEW_CHANGE: False} for i in range(5)] + [{
                REP_STATE: {},
                R_LOG: [],
                PEND_REQS: [],
                REQ_Q: [],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(6,6)]

        self.assertTrue(replication.conflict())
        
        # All but two node have their conflict flag to True, meaning less than 4f+1
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: True,
            VIEW_CHANGE: False} for i in range(4)] + [{
                REP_STATE: {},
                R_LOG: [],
                PEND_REQS: [],
                REQ_Q: [],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(5,6)]

        self.assertFalse(replication.conflict())

    def test_com_pref_states(self):
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)
        replication.rep[0][REP_STATE] = [{"op": "add", "val": 0}]
        replication.rep[1][REP_STATE] = [{"op": "add", "val": 0}]
        replication.rep[2][REP_STATE] = [{"op": "add", "val": 1}]
        replication.rep[3][REP_STATE] = [{"op": "add", "val": 0}, {"op": "add", "val": 2}]
        replication.rep[4][REP_STATE] = [{"op": "add", "val": 3}]
        replication.rep[5][REP_STATE] = [{"op": "add", "val": 2}]

        self.assertEqual(replication.com_pref_states(2), ([{"op": "add", "val": 0}], [{"op": "add", "val": 0}]))
        self.assertEqual(replication.com_pref_states(3), ([{"op": "add", "val": 0}], [{"op": "add", "val": 0}],[{"op": "add", "val": 0}, {"op": "add", "val": 2}]))
        # no more than 3 processors have a common prefix
        self.assertEqual(replication.com_pref_states(4), set())


    def test_double(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        
        replication.rep[0][REQ_Q] = [{REQUEST: self.dummyRequest1, STATUS:{}},
                    {REQUEST: self.dummyRequest2, STATUS:{}}]
        self.assertFalse(replication.double())

        # Adding a copy of message dummyRequest1 but with different sequence number,
        double_message = {CLIENT_REQ: {1}, VIEW: 1, SEQUENCE_NO: 2}
        replication.rep[replication.id][REQ_Q].append({REQUEST: double_message, STATUS:{}})
        self.assertTrue(replication.double())

    def test_stale_req_seqn(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)

        # The replica has executed a request with sequence number within the threshold
        replication.last_exec = MagicMock(return_value = 1)
        self.assertFalse(replication.stale_req_seqn())

        # The replica has executed a request with sequence number outside the threshold
        replication.last_exec = MagicMock(return_value = sys.maxsize - SIGMA + 1)
        self.assertTrue(replication.stale_req_seqn())

    def test_unsup_req(self):
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)

        # All processors have the same req_q, so there is no unsupported msg
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [{REQUEST: self.dummyRequest1, STATUS:{}},
                    {REQUEST: self.dummyRequest2, STATUS:{}}],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(6)]

        self.assertFalse(replication.unsup_req())

        # Processor 0 has one unsupported request (dummyRequest2)
        # The rest does not have dummyRequest2 in their REQ_Q
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [{REQUEST: self.dummyRequest1, STATUS:{}},
                    {REQUEST: self.dummyRequest2, STATUS:{}}],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(1)] + [{
                REP_STATE: {},
                R_LOG: [],
                PEND_REQS: [],
                REQ_Q: [{REQUEST: self.dummyRequest1, STATUS:{}}],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(1,6)]

        self.assertTrue(replication.unsup_req())

    def test_stale_rep(self):
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)
        replication.stale_req_seqn = MagicMock(return_value = False)
        replication.double = MagicMock(return_value = False)
        replication.unsup_req = MagicMock(return_value = False)

        # Processor has a request in R_LOG that has enough processor in its X_SET
        replication.rep[replication.id][R_LOG] = [{REQUEST: self.dummyRequest2, X_SET:{1,2,3,4,5}}]
        self.assertFalse(replication.stale_rep())

        # Processor has a request in R_LOG that doesn't have enough processor in its X_SET
        replication.rep[replication.id][R_LOG] = [{REQUEST: self.dummyRequest2, X_SET:{3,4,5}}]
        self.assertTrue(replication.stale_rep())

        # The other methods should be called twice (calling the method twice in the test)
        self.assertEqual(replication.stale_req_seqn.call_count, 2)
        self.assertEqual(replication.double.call_count, 2)
        self.assertEqual(replication.unsup_req.call_count, 2)

    def test_known_pend_reqs(self):
        replication = ReplicationModule(0, self.resolver, 4, 1, 1)
        # Node 0 has both dummyRequests in pend queue
        # Node 1-3 have dummyRequest1 in request queue
        # Node 4-5 have dummyRequest1 in pend queue
        # This means that known pending request are dummyRequest 1
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [self.dummyRequest1,
                    self.dummyRequest2],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(1)] + [{
                REP_STATE: {},
                R_LOG: [],
                PEND_REQS: [],
                REQ_Q: [{REQUEST: self.dummyRequest1, STATUS:{}}],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(1,4)] + [{
                    REP_STATE: {},
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest1],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: False} for i in range(4,6)
                ]
        self.assertEqual(replication.known_pend_reqs(), [self.dummyRequest1])

        # No known pending request found, only 3 processor has dummyRequest1
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [self.dummyRequest1,
                    self.dummyRequest2],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(1)] + [{
                REP_STATE: {},
                R_LOG: [],
                PEND_REQS: [],
                REQ_Q: [{REQUEST: self.dummyRequest1, STATUS:{}}],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(1,3)] + [{
                    REP_STATE: {},
                    R_LOG: [],
                    PEND_REQS: [],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: False} for i in range(3,6)
                ]
        self.assertEqual(replication.known_pend_reqs(), [])

    def test_known_reqs(self):
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)
        # Node 0 has both requests in request queue, the others have only request 1 with 
        # same status, should therefore return dummyRequest1
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP},
                    {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP }],
             LAST_REQ: [],
             CON_FLAG: False,
             VIEW_CHANGE: False} for i in range(1)] + [{
                REP_STATE: {},
                R_LOG: [],
                PEND_REQS: [],
                REQ_Q: [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP }],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(1,6)
                ]
        
        self.assertEqual(
            replication.known_reqs({ReplicationEnums.PRE_PREP}), 
            [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP}])

        # Asserting that the convertion to a set of the status works
        self.assertEqual(
            replication.known_reqs(ReplicationEnums.PRE_PREP), 
            [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP}])

        # Node 0 has both requests in request queue, the others have only request 1 with 
        # other status, should therefore return empty
        replication.rep = [{
             REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP},
                    {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP}],
             LAST_REQ: [],
             CON_FLAG: False,
             VIEW_CHANGE: False} for i in range(1)] + [{
                REP_STATE: {},
                R_LOG: [],
                PEND_REQS: [],
                REQ_Q: [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.COMMIT}],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(1,6)
                ]
        
        self.assertEqual(
            replication.known_reqs({ReplicationEnums.COMMIT}), 
            [])

        # Should return dummyRequest1 eventhough they have different statuses,
        # since the other processor has this request with a status in the 
        # input stats (PRE_PREP, COMMIT)
        self.assertEqual(
            replication.known_reqs({ReplicationEnums.PRE_PREP, ReplicationEnums.COMMIT}),
            [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP}]
        )

    def test_delay(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        
        # Last execution will be within the threshold
        replication.last_common_exec = MagicMock(return_value = 3)
        replication.last_exec = MagicMock(return_value = 3)
        self.assertFalse(replication.delayed())

        # Last execution will be smaller than the threshold 
        replication.last_common_exec = MagicMock(return_value = 40)
        replication.last_exec = MagicMock(return_value = 3)
        self.assertTrue(replication.delayed())

    def test_exists_preprep_msg(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        # Primary is set to processor 1, with a PRE_PREP msg for dummyRequst 1
        replication.prim = 1
        replication.rep[1][REQ_Q] = [
            {REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP},
            {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP}]

        self.assertTrue(replication.exists_preprep_msg(self.dummyRequest1[CLIENT_REQ], 1))
        # No Pre_prep msg for dummyRequest2
        self.assertFalse(replication.exists_preprep_msg(self.dummyRequest2[CLIENT_REQ], 1))
        # Node 0 is not prim, and there exists no Pre_prep msg in rep[0]
        self.assertFalse(replication.exists_preprep_msg(self.dummyRequest1[CLIENT_REQ], 0))

    def test_unassigned_reqs(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        replication.rep[0][PEND_REQS] = [self.dummyRequest1, self.dummyRequest2]

        # Both requests are unassigned
        replication.exists_preprep_msg = MagicMock(return_value = False)
        replication.known_reqs = MagicMock(return_value = [])
        self.assertEqual(replication.unassigned_reqs(), [self.dummyRequest1, self.dummyRequest2])
        calls = [call(self.dummyRequest1, replication.prim), call(self.dummyRequest2, replication.prim)]
        replication.exists_preprep_msg.assert_has_calls(calls)
       
        # Dummyrequest2 is in known_reqs with
        replication.known_reqs = MagicMock(return_value = [self.dummyRequest2])
        self.assertEqual(replication.unassigned_reqs(), [self.dummyRequest1])

        # There exists PRE_PREP msg for both of the requests
        replication.exists_preprep_msg = MagicMock(return_value = True)
        self.assertEqual(replication.unassigned_reqs(), [])

    def test_committed_set(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)

        # The other processor (1) has the dummyRequest2 in it's R_LOG but the msg-function does not
        # return any
        replication.rep[1][R_LOG] = [{REQUEST: self.dummyRequest2, X_SET: {5}}]
        replication.msg = MagicMock(return_value = [])
        self.assertEqual(replication.committed_set(self.dummyRequest2), {1})

        # The msg will return dummyRequest1 for both processors but it is not in R_LOG for any of the processors
        replication.rep[1][R_LOG] = []
        replication.msg = MagicMock(return_value = [self.dummyRequest1])
        self.assertEqual(replication.committed_set(self.dummyRequest1),{0, 1})
        # No condition for dummyRequest2 will now be true
        self.assertEqual(replication.committed_set(self.dummyRequest2),set())

    # Interface functions

    def test_get_pend_reqs(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)

        # Should return the intersection of the two sets, meaning {2}
        replication.unassigned_reqs = MagicMock(return_value = {1,2})
        replication.known_pend_reqs = MagicMock(return_value = {2,3})
        replication.view_changed = False
        self.assertEqual(replication.get_pend_reqs(), {2})

    def test_rep_request_reset(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)

        # Should return false
        replication.need_flush = False
        self.assertFalse(replication.rep_request_reset())

        # Should change need_flush and return true
        replication.need_flush = True
        self.assertTrue(replication.rep_request_reset())
        self.assertFalse(replication.need_flush)

    def test_replica_flush(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)

        # Should change flush to True
        replication.flush = False
        replication.replica_flush()
        self.assertTrue(replication.flush)

    # Added functions

    def test_prefixes(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)

        # Basic examples
        log_A = [1,2,3]
        log_B = [1,2]
        self.assertTrue(replication.prefixes(log_A, log_B))
        self.assertTrue(replication.prefixes(log_B, log_A))

        log_B = [1,2,5]
        self.assertFalse(replication.prefixes(log_A, log_B))
        
        log_A = []
        self.assertTrue(replication.prefixes(log_A, log_B))

        # Examples with dcts
        log_A = [{REQUEST: self.dummyRequest1, X_SET:{2}}]
        log_B = [{REQUEST: self.dummyRequest1, X_SET:{2}}, 
                {REQUEST: self.dummyRequest2, X_SET:{1,3}}, 
                ]
        self.assertTrue(replication.prefixes(log_A, log_B))
        
        log_A = [{REQUEST: self.dummyRequest1, X_SET:{2,4}}]
        log_B = [{REQUEST: self.dummyRequest1, X_SET:{2}}, 
                {REQUEST: self.dummyRequest2, X_SET:{1,3}}, 
                ]
        self.assertFalse(replication.prefixes(log_A, log_B))