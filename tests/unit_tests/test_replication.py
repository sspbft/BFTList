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
                               SIGMA, PRIM, REPLY, CLIENT)

class TestReplicationModule(unittest.TestCase):

    def setUp(self):
        self.resolver = Resolver()
        self.dummyRequest1 = {CLIENT_REQ: {CLIENT: 0}, VIEW: 1, SEQUENCE_NO: 1}
        self.dummyRequest2 = {CLIENT_REQ: {CLIENT: 2}, VIEW: 1, SEQUENCE_NO: 2}
    
    def test_resolver_can_be_initialized(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        self.assertIsNotNone(replication)

    # Macros

    def test_flush_local(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        replication.flush_local()
        # The local variables should be the default values
        rep_default = [{REP_STATE: [],
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
             VIEW_CHANGE: False,
             PRIM: -1},
             {REP_STATE: [],
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
             VIEW_CHANGE: False,
             PRIM: -1}]
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
             REP_STATE: [],
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
             REP_STATE: [],
             R_LOG: [{REQUEST: self.dummyRequest1, X_SET:{}}],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(2)] + [{
                REP_STATE: [],
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
             REP_STATE: [],
             R_LOG: [{REQUEST: self.dummyRequest1, X_SET:{0,1,2}}],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(2)] + [{
                REP_STATE: [],
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
             REP_STATE: [],
             R_LOG: [{REQUEST: self.dummyRequest1, X_SET:{0,1,2,3,4,5}}],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(2)] + [{
                REP_STATE: [],
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
             REP_STATE: [],
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: True,
            VIEW_CHANGE: False} for i in range(5)] + [{
                REP_STATE: [],
                R_LOG: [],
                PEND_REQS: [],
                REQ_Q: [],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(6,6)]

        self.assertTrue(replication.conflict())
        
        # All but two node have their conflict flag to True, meaning less than 4f+1
        replication.rep = [{
             REP_STATE: [],
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: True,
            VIEW_CHANGE: False} for i in range(4)] + [{
                REP_STATE: [],
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

    def test_get_ds_state(self):
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)
        replication.rep[0][REP_STATE] = [{"op": "add", "val": 0}]
        replication.rep[1][REP_STATE] = [{"op": "add", "val": 0}]
        replication.rep[2][REP_STATE] = [{"op": "add", "val": 1}]
        replication.rep[3][REP_STATE] = [{"op": "add", "val": 0}, {"op": "add", "val": 2}]
        replication.rep[4][REP_STATE] = []
        replication.rep[5][REP_STATE] = []

        replication.find_cons_state = MagicMock(return_value = [{"op": "add", "val": 0}])
        self.assertEqual(replication.get_ds_state(), [{"op": "add", "val": 0}])
        
        # Not enough processors with the state found in find_cons_state
        replication.rep[0][REP_STATE] = [{"op": "add", "val": 2}]
        replication.rep[1][REP_STATE] = [{"op": "add", "val": 4}]
        self.assertEqual(replication.get_ds_state(), -1)

    def test_double(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        
        replication.rep[0][REQ_Q] = [{REQUEST: self.dummyRequest1, STATUS:{}},
                    {REQUEST: self.dummyRequest2, STATUS:{}}]
        self.assertFalse(replication.double())

        # Adding a copy of message dummyRequest1 but with different sequence number,
        double_message = {CLIENT_REQ: {CLIENT: 0}, VIEW: 1, SEQUENCE_NO: 2}
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
             REP_STATE: [],
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
             REP_STATE: [],
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [{REQUEST: self.dummyRequest1, STATUS:{}},
                    {REQUEST: self.dummyRequest2, STATUS:{}}],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(1)] + [{
                REP_STATE: [],
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
             REP_STATE: [],
             R_LOG: [],
             PEND_REQS: [self.dummyRequest1,
                    self.dummyRequest2],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(1)] + [{
                REP_STATE: [],
                R_LOG: [],
                PEND_REQS: [],
                REQ_Q: [{REQUEST: self.dummyRequest1, STATUS:{}}],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(1,4)] + [{
                    REP_STATE: [],
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
             REP_STATE: [],
             R_LOG: [],
             PEND_REQS: [self.dummyRequest1,
                    self.dummyRequest2],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(1)] + [{
                REP_STATE: [],
                R_LOG: [],
                PEND_REQS: [],
                REQ_Q: [{REQUEST: self.dummyRequest1, STATUS:{}}],
                LAST_REQ: [],
                CON_FLAG: False,
                VIEW_CHANGE: False} for i in range(1,3)] + [{
                    REP_STATE: [],
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
             REP_STATE: [],
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP},
                    {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP }],
             LAST_REQ: [],
             CON_FLAG: False,
             VIEW_CHANGE: False} for i in range(1)] + [{
                REP_STATE: [],
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
             REP_STATE: [],
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP},
                    {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP}],
             LAST_REQ: [],
             CON_FLAG: False,
             VIEW_CHANGE: False} for i in range(1)] + [{
                REP_STATE: [],
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
        calls = [
            call(self.dummyRequest1, replication.rep[replication.id][PRIM]),
            call(self.dummyRequest2, replication.rep[replication.id][PRIM])
        ]
        replication.exists_preprep_msg.assert_has_calls(calls)
       
        # Dummyrequest2 is in known_reqs with
        replication.known_reqs = MagicMock(return_value = [{REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.COMMIT}])
        self.assertEqual(replication.unassigned_reqs(), [self.dummyRequest1])

        # There exists PRE_PREP msg for both of the requests
        replication.exists_preprep_msg = MagicMock(return_value = True)
        self.assertEqual(replication.unassigned_reqs(), [])

    def test_accept_req_preprep(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)

        replication.known_pend_reqs = MagicMock(return_value = [self.dummyRequest1, self.dummyRequest2])
        replication.exists_preprep_msg = MagicMock(return_value = True)
        replication.last_exec = MagicMock(return_value = 0)
        replication.rep[replication.id][REQ_Q] = [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP},
                    {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP}]

        # The dummyRequest1 should be accepted
        self.assertTrue(replication.accept_req_preprep(self.dummyRequest1, self.dummyRequest1[VIEW]))

        # Request has a sequence number outside the threshold
        dummyRequest3 = {CLIENT_REQ: {2}, VIEW: 1, SEQUENCE_NO: 10000}
        replication.known_pend_reqs = MagicMock(return_value = [dummyRequest3])
        replication.rep[replication.id][REQ_Q] = [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP},
            {REQUEST: dummyRequest3, STATUS: ReplicationEnums.PREP}]
        self.assertFalse(replication.accept_req_preprep(dummyRequest3, 1))

        # The input prim does not match any of the requests
        dummyRequest3 = {CLIENT_REQ: {2}, VIEW: 1, SEQUENCE_NO: 1}
        replication.known_pend_reqs = MagicMock(return_value = [dummyRequest3])
        replication.rep[replication.id][REQ_Q] = [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP},
            {REQUEST: dummyRequest3, STATUS: ReplicationEnums.PREP}]
        self.assertFalse(replication.accept_req_preprep(dummyRequest3, 2))
        
        # The dummyRequest1 (input) does not exists in known_pend_reqs
        replication.known_pend_reqs = MagicMock(return_value = [self.dummyRequest2])
        self.assertFalse(replication.accept_req_preprep(self.dummyRequest1, self.dummyRequest1[VIEW]))

        # Now the request already exists in REQ_Q (checks the logic of already_exists)
        replication.known_pend_reqs = MagicMock(return_value = [self.dummyRequest1, self.dummyRequest2])
        replication.rep[replication.id][REQ_Q] = [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PREP},
            {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP},
            {REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP}]
        self.assertFalse(replication.accept_req_preprep(self.dummyRequest1, self.dummyRequest1[VIEW]))
        
        # The dummyRequest2 on the other hand should be accepted
        self.assertTrue(replication.accept_req_preprep(self.dummyRequest2, self.dummyRequest2[VIEW]))

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
    def test_request_already_exists(self):
        replication = ReplicationModule(0, self.resolver, 2, 0, 1)
        dummyRequest3 = {CLIENT_REQ: {CLIENT:0}, VIEW: 2, SEQUENCE_NO: 1}
        # The request does not already exist with a different status
        replication.rep[replication.id][REQ_Q] = [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP},
                                                  {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP}]
        self.assertFalse(replication.request_already_exists({REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP}))
        
        # dummyRequest1 already exists with a different status
        replication.rep[replication.id][REQ_Q] = [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PREP},
                                                  {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP}]
        self.assertTrue(replication.request_already_exists({REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP}))

        # dummyRequest3 is the same as dummyRequest2 beside the view -> found duplicate of sq_no and q
        replication.rep[replication.id][REQ_Q] = [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PREP},
                                            {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP},
                                            {REQUEST: dummyRequest3, STATUS: ReplicationEnums.PREP}]
        self.assertTrue(replication.request_already_exists({REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PREP}))

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

    # Tests for while true-loop

    def test_act_as_prim_when_view_changed(self):
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)
        replication.rep = [{
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest1],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: True} for i in range(6)
                ]
        # Pretend prim == replication.id (0)
        replication.resolver.execute = MagicMock(return_value = replication.id)
        replication.renew_reqs = Mock()
        replication.find_cons_state = Mock()
        # All nodes are in the processor set, because all has the same rep
        replication.act_as_prim_when_view_changed(replication.id)
        replication.find_cons_state.assert_called_once()
        replication.renew_reqs.assert_called_once_with({0,1,2,3,4,5})
        self.assertFalse(replication.rep[replication.id][VIEW_CHANGE])

        # Half of nodes has declared a view change, half has not
        replication.rep = [{
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest1],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: True} for i in range(3)
                ] + [{
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest1],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: False} for i in range(3,6)
                ]

        # Pretend prim == replication.id (0)
        replication.resolver.execute = MagicMock(return_value = replication.id)
        replication.renew_reqs = Mock()
        replication.find_cons_state = Mock()
        # Half of the nodes are in the set so it's less than 4f+1,
        #  methods should not be called and view_change = True
        replication.act_as_prim_when_view_changed(replication.id)
        replication.renew_reqs.assert_not_called()
        replication.find_cons_state.assert_not_called()
        self.assertTrue(replication.rep[replication.id][VIEW_CHANGE])

        # All has declared a view change but not all has 0 as prim
        replication.rep = [{
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest1],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: True} for i in range(6)
                ]
        # Pretend prim == replication.id % 2 => half will say 0, half will say 1
        replication.resolver.execute = MagicMock(side_effect = lambda y, z, x: x % 2)
        replication.renew_reqs = Mock()
        replication.find_cons_state = Mock()
        # All nodes are in the processor set, because all has the same rep
        replication.act_as_prim_when_view_changed(replication.id)
        replication.find_cons_state.assert_not_called()
        replication.renew_reqs.assert_not_called()
        self.assertTrue(replication.rep[replication.id][VIEW_CHANGE])

    def test_act_as_nonprim_when_view_changed(self):
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)

        # Prim will be node 5, has a different replica strucutre
        replication.rep = [{
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest1],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: True} for i in range(5)
                ] + [{
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest2],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: False}
                ]
        # Everybody has 5 as prim and check_new_v_state returns True
        replication.resolver.execute = MagicMock(return_value = 5)
        replication.check_new_v_state = MagicMock(return_vale = True)
        replication.act_as_nonprim_when_view_changed(5)

        self.assertFalse(replication.rep[replication.id][VIEW_CHANGE])
        self.assertEqual(replication.rep[replication.id], {
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest2],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: False})

        # The replica should not accept node 5's rep state
        replication.rep = [{
            REP_STATE: [],
            R_LOG: [],
            PEND_REQS: [self.dummyRequest1],
            REQ_Q: [],
            LAST_REQ: [],
            CON_FLAG: False,
            VIEW_CHANGE: True} for i in range(5)
        ] + [{
            REP_STATE: [],
            R_LOG: [],
            PEND_REQS: [self.dummyRequest2],
            REQ_Q: [],
            LAST_REQ: [],
            CON_FLAG: False,
            VIEW_CHANGE: False}
        ]
        # Should not accept node 5's rep and view Change should stay true
        replication.check_new_v_state = MagicMock(return_value = False)
        replication.act_as_nonprim_when_view_changed(5)
        self.assertTrue(replication.rep[replication.id][VIEW_CHANGE])
        self.assertNotEqual(replication.rep[replication.id], {
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest2],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: False})

        # Prim will be node 1, has a different replica structure
        replication.rep = [{
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest2],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: True}
                ] + [{
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest1],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: False}
                ] + [{
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest2],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: True} for i in range(2,6)
                ]
        # less than 4f+1 has 0 as prim but check_new_v_state returns True
        replication.resolver.execute = MagicMock(side_effect = lambda y, z, x: x % 2)
        replication.check_new_v_state = MagicMock(return_vale = True)
        replication.act_as_nonprim_when_view_changed(1)

        self.assertTrue(replication.rep[replication.id][VIEW_CHANGE])
        self.assertNotEqual(replication.rep[replication.id], {
                    REP_STATE: [],
                    R_LOG: [],
                    PEND_REQS: [self.dummyRequest1],
                    REQ_Q: [],
                    LAST_REQ: [],
                    CON_FLAG: False,
                    VIEW_CHANGE: False})

    def test_reqs_to_prep(self):
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)
        # DummyRequest1 exists in unassigned_reqs
        replication.unassigned_reqs = MagicMock(return_value = [self.dummyRequest1])
        self.assertFalse(replication.reqs_to_prep(self.dummyRequest1))

        # DummyRequest1 does not exist in unassigned_reqs but in rep[REQ_Q]
        replication.unassigned_reqs = MagicMock(return_value = [])
        replication.rep[replication.id][REQ_Q] = [{REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP}]
        self.assertFalse(replication.reqs_to_prep(self.dummyRequest1))

        # DummyRequest2 is accepted
        replication.accept_req_preprep = MagicMock(return_value = True)
        self.assertTrue(replication.reqs_to_prep(self.dummyRequest2))

    def test_commit(self):
        replication = ReplicationModule(0, self.resolver, 6, 1, 2)
        replication.apply = MagicMock(return_value = "REPLY")

        replication.rep[replication.id] = {
            REP_STATE: [],
            R_LOG: [],
            PEND_REQS: [self.dummyRequest1, self.dummyRequest2],
            REQ_Q: [{REQUEST: self.dummyRequest1, STATUS: [ReplicationEnums.PRE_PREP, ReplicationEnums.PREP, ReplicationEnums.COMMIT]}],
            LAST_REQ: [None],
            CON_FLAG: False,
            VIEW_CHANGE: True}

        # Commit should removed dummyRequest 1 from pend_reqs and req_q and add to last_req and R_log
        replication.commit({REQUEST: self.dummyRequest1, STATUS: [ReplicationEnums.PRE_PREP, ReplicationEnums.PREP, ReplicationEnums.COMMIT]})
        # Apply should be called once with self.dummyRequest1
        replication.apply.assert_called_once_with(self.dummyRequest1)
        self.assertEqual(replication.rep[replication.id], {
            REP_STATE: [],
            LAST_REQ: [{REQUEST: self.dummyRequest1, REPLY: 'REPLY'}],
            R_LOG: [{REQUEST: self.dummyRequest1, STATUS: [ReplicationEnums.PRE_PREP, ReplicationEnums.PREP, ReplicationEnums.COMMIT]}],
            PEND_REQS: [self.dummyRequest2],
            REQ_Q: [],
            CON_FLAG: False,
            VIEW_CHANGE: True}
        )

    def test_while_check_for_view_change(self):
        # Line 1-3
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = Mock()
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = False)
        replication.last_exec = Mock()
        replication.unassigned_reqs = Mock()
        replication.committed_set = Mock()
        replication.reqs_to_prep = Mock()
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()
        replication.flush_local = Mock()
        replication.prefixes = MagicMock(return_value = True)

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        replication.find_cons_state = MagicMock(return_value = [])
        replication.get_ds_state = MagicMock(return_value = [])
        replication.known_pend_reqs = MagicMock(return_value = [])

        # The resolver should return the current view (0)
        replication.resolver.execute = MagicMock(side_effect = lambda y, func, x=-1 : self.get_0_as_view(func))
        replication.run()
        # Node started with DEF_STATE, should have changed the following parameters
        self.assertEqual(replication.rep[replication.id][PRIM], 0)
        self.assertFalse(replication.rep[replication.id][VIEW_CHANGE])

        # The view change should be set to True, our prim is different from what algo 2 
        # returns
        replication.rep = [{
            REP_STATE: [],
            R_LOG: [],
            PEND_REQS: [],
            REQ_Q: [],
            LAST_REQ: [],
            CON_FLAG: False,
            VIEW_CHANGE: False,
            PRIM: 5} for i in range(6)
        ] 
        replication.run()
        self.assertEqual(replication.rep[replication.id][PRIM], 0)
        self.assertTrue(replication.rep[replication.id][VIEW_CHANGE])

    def test_while_view_change_occur_check_calls(self):
        # Line 4-8
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = Mock()
        replication.stale_rep = Mock()
        replication.conflict = Mock()
        replication.last_exec = Mock()
        replication.unassigned_reqs = Mock()
        replication.committed_set = Mock()
        replication.reqs_to_prep = Mock()
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()

        replication.find_cons_state = MagicMock(return_value = [])
        replication.get_ds_state = MagicMock(return_value = [])
        replication.known_pend_reqs = MagicMock(return_value = [])

        # Used to set prim of self.id
        # Node 0 is prim
        replication.resolver.execute = MagicMock(return_value = 0)
        replication.rep = [{
            REP_STATE: [],
            R_LOG: [],
            PEND_REQS: [],
            REQ_Q: [],
            LAST_REQ: [],
            CON_FLAG: False,
            VIEW_CHANGE: True,
            PRIM: 0} for i in range(6)
        ] 

        replication.run()
        replication.act_as_prim_when_view_changed.assert_called_once()

        replication.rep = [{
            REP_STATE: [],
            R_LOG: [],
            PEND_REQS: [],
            REQ_Q: [],
            LAST_REQ: [],
            CON_FLAG: False,
            VIEW_CHANGE: True,
            PRIM: 5} for i in range(5)
        ] + [{
            REP_STATE: [],
            R_LOG: [],
            PEND_REQS: [],
            REQ_Q: [],
            LAST_REQ: [],
            CON_FLAG: False,
            VIEW_CHANGE: False,
            PRIM: 5}
        ]
        # Node 0 is NOT primary anymore, node 5 is
        replication.resolver.execute = MagicMock(return_value = 5)
        replication.run()
        replication.act_as_nonprim_when_view_changed.assert_called_once()

    def test_while_finding_consolidated_state(self):
        # Line 9-11
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = Mock()
        replication.last_exec = Mock()
        replication.unassigned_reqs = Mock()
        replication.committed_set = Mock()
        replication.reqs_to_prep = Mock()
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        # These functions are not used for the current case of test
        replication.get_ds_state = MagicMock(return_value = [])
        replication.resolver.execute = MagicMock(return_value = -1)
        replication.known_pend_reqs = MagicMock(return_value = [])

        # The consolidated state is mock_rep_state
        mock_rep_state = [1,2]
        replication.find_cons_state = MagicMock(return_value = [mock_rep_state])
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = False)

        # Node 0 has DEF_STATE, should "adopt" mock_rep_state
        replication.run()
        self.assertFalse(replication.rep[replication.id][CON_FLAG])
        self.assertEqual(replication.rep[replication.id][REP_STATE], [mock_rep_state])

        # Node 0 REP_STATE is not a prefix of mock_rep_state and should adopt
        replication.rep = [{
            REP_STATE: [[7]],
            R_LOG: [],
            PEND_REQS: [],
            REQ_Q: [],
            LAST_REQ: [],
            CON_FLAG: False,
            VIEW_CHANGE: False,
            PRIM: 4} for i in range(6)
        ] 
        replication.run()
        self.assertEqual(replication.rep[replication.id][REP_STATE], [mock_rep_state])

    
    def test_while_reset_cases(self):
        # Lines 12-13
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = Mock()
        replication.last_exec = Mock()
        replication.unassigned_reqs = Mock()
        replication.committed_set = Mock()
        replication.reqs_to_prep = Mock()
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()
        replication.flush_local = Mock()

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        replication.find_cons_state = MagicMock(return_value = [])
        replication.get_ds_state = MagicMock(return_value = [])
        replication.resolver.execute = MagicMock(return_value = 0)
        replication.known_pend_reqs = MagicMock(return_value = [])

        # Specific mock-calls for this case test
        replication.stale_rep = MagicMock(return_value = True)
        replication.conflict = MagicMock(return_value = False)

        # The node does not have DEF_STATE
        replication.rep = [{
            REP_STATE: [],
            R_LOG: [],
            PEND_REQS: [self.dummyRequest1],
            REQ_Q: [],
            LAST_REQ: [],
            CON_FLAG: False,
            VIEW_CHANGE: True,
            PRIM: 2} for i in range(6)
        ] 
        # The node should flush it's rep, meaning having DEF_STATE
        replication.need_flush = False
        replication.run()
        self.assertTrue(replication.need_flush)
        # Need to have the dummy 2 just because extend of a empty mock-list is
        # biting my ass
        self.assertEqual(replication.rep[replication.id], replication.DEF_STATE)
        replication.flush_local.assert_called_once()

        # Specific mock-calls for this case test
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = True)

        # The node does not have DEF_STATE
        replication.rep = [{
            REP_STATE: [],
            R_LOG: [],
            PEND_REQS: [self.dummyRequest1],
            REQ_Q: [],
            LAST_REQ: [],
            CON_FLAG: False,
            VIEW_CHANGE: True,
            PRIM: 2} for i in range(6)
        ] 
        # The node should flush it's rep, meaning having DEF_STATE
        replication.need_flush = False
        replication.flush_local = Mock()
        replication.run()
        self.assertTrue(replication.need_flush)
        # Need to have the dummy 2 just because extend of a empty mock-list is
        # biting my ass
        self.assertEqual(replication.rep[replication.id], replication.DEF_STATE)
        replication.flush_local.assert_called_once()

        # Just testing flush = True -> flush_local called
        replication.flush = True
        replication.flush_local = Mock()
        replication.run()
        # Being called twice, once on line 12 and once in line 13
        self.assertEqual(replication.flush_local.call_count, 2)

    def template_for_while_true(self):
        replication = ReplicationModule(0, self.resolver, 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = Mock()
        replication.stale_rep = Mock()
        replication.conflict = Mock()
        replication.known_pend_reqs = Mock()
        replication.last_exec = Mock()
        replication.unassigned_reqs = Mock()
        replication.committed_set = Mock()
        replication.reqs_to_prep = Mock()
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        replication.find_cons_state = MagicMock(return_value = [])
        replication.get_ds_state = MagicMock(return_value = [])
        replication.resolver.execute = MagicMock(return_value = 0)

        replication.rep = [{
            REP_STATE: [],
            R_LOG: [],
            PEND_REQS: [],
            REQ_Q: [],
            LAST_REQ: [],
            CON_FLAG: False,
            VIEW_CHANGE: True,
            PRIM: 0} for i in range(6)
        ] 

    # Functions used to mock execute at resolver
    def get_0_as_view(self, func):
        if (func == Function.ALLOW_SERVICE):
            return True
        else:
            return 0