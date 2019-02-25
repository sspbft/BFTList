# standard
import unittest
from unittest.mock import Mock, MagicMock, call
import sys

# local
from resolve.resolver import Resolver
from modules.replication.module import ReplicationModule
from resolve.enums import Function, Module
from modules.enums import ReplicationEnums, OperationEnums
from modules.constants import (REP_STATE, R_LOG, PEND_REQS, REQ_Q,
                               LAST_REQ, CON_FLAG, VIEW_CHANGE,
                               REQUEST, SEQUENCE_NO, STATUS, VIEW, X_SET, CLIENT_REQ,
                               SIGMA, PRIM, REPLY, CLIENT)
from modules.replication.models.replica_structure import ReplicaStructure
from modules.replication.models.request import Request
from modules.replication.models.client_request import ClientRequest
from modules.replication.models.operation import Operation

class TestReplicationModule(unittest.TestCase):

    def setUp(self):
        self.dummyRequest1 = Request(ClientRequest(0, None, Operation(
            OperationEnums.APPEND, 1
        )), 1, 1)
        self.dummyRequest2 = Request(ClientRequest(2, None, Operation(
            OperationEnums.APPEND, 2
        )), 1, 2)
    
    def test_resolver_can_be_initialized(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)
        self.assertIsNotNone(replication)

    # Macros
    def test_flush_local(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)
        replication.flush_local()
        # The local variables should be the default values
        one = replication.rep[0]
        two = replication.rep[1]
        self.assertEqual(one.get_rep_state(), two.get_rep_state())
        self.assertEqual(one.get_r_log(), two.get_r_log())
        self.assertEqual(one.get_pend_reqs(), two.get_pend_reqs())
        self.assertEqual(one.get_req_q(), two.get_req_q())
        self.assertEqual(one.get_last_req(), two.get_last_req())
        self.assertEqual(one.get_con_flag(), two.get_con_flag())
        self.assertEqual(one.get_view_changed(), two.get_view_changed())
        self.assertEqual(one.get_prim(), two.get_prim())

    def test_msg(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)
        replication.rep[1].set_req_q([
                {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}},
                {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PREP} }])

        self.assertEqual(replication.msg({ReplicationEnums.PRE_PREP}, 1), [self.dummyRequest1])
        self.assertEqual(replication.msg({ReplicationEnums.PREP}, 1), [self.dummyRequest2])
        self.assertEqual(replication.msg({ReplicationEnums.COMMIT}, 1), [])

    def test_last_execution(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)
        # The last executed is dummyRequest 2 with sequence number 2
        replication.rep[replication.id].set_r_log([{REQUEST: self.dummyRequest1, X_SET: {5}},
                                  {REQUEST: self.dummyRequest2, X_SET: {5}}])

        self.assertEqual(replication.last_exec(), 2)
        # There is no executed requests
        replication.rep[replication.id].set_r_log([])

        self.assertEqual(replication.last_exec(), -1)
        

    def test_last_common_execution(self):
        # 5 nodes, 1 byzantine
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        replication.rep = [ReplicaStructure(
            i,
            r_log=[{REQUEST: self.dummyRequest1, X_SET: set()},{REQUEST: self.dummyRequest2, X_SET:{0,1,2,3,4,5}}]
        ) for i in range(6)]

        self.assertEqual(replication.last_common_exec(), 2)

        # There is no common last executed request, 3 nodes have
        # request 1 and 3 nodes have not executed anything.
        replication.rep = [ReplicaStructure(
            i,
            r_log=[{REQUEST: self.dummyRequest1, X_SET:{0,1,2}}]
        ) for i in range(3)] + [ReplicaStructure(
            i,
            r_log = []
        ) for i in range(3, 6)]
        self.assertIsNone(replication.last_common_exec())

        # There is no common last executed request, 3 nodes have request 1 and 2 nodes request 2
        # This case should not happen, the last 2 nodes should not be able to add request 2 without
        # seeing request 2. But it checks the logic of the function.
        replication.rep = [ReplicaStructure(
            i,
            r_log=[{REQUEST: self.dummyRequest1, X_SET:{}}]
        ) for i in range(3)] + [ReplicaStructure(
            i,
            r_log=[{REQUEST: self.dummyRequest2, X_SET:{3,4,5}}]
        ) for i in range(3, 6)]

        self.assertIsNone(replication.last_common_exec())

        # The common last executed request is request 1 (sequence number 1)
        # 3 nodes have only request 1 and 2 nodes request 1 and request 2
        replication.rep = [ReplicaStructure(
            i,
            r_log=[{REQUEST: self.dummyRequest1, X_SET:{0,1,2,3,4,5}}]
        ) for i in range(2)] + [ReplicaStructure(
            i,
            r_log=[{REQUEST: self.dummyRequest1, X_SET:{0,1,2,3,4,5}},{REQUEST: self.dummyRequest2, X_SET:{3,4,5}}]
        ) for i in range(3, 5)]

        self.assertEqual(replication.last_common_exec(), 1)

    def test_conflict(self):
        # 6 nodes 1 byzantine
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)

        # All but one node have their conflict flag to True
        replication.rep = [ReplicaStructure(
            i,
            con_flag=True
        ) for i in range(5)] + [ReplicaStructure(5)]

        self.assertTrue(replication.conflict())
        
        # All but two node have their conflict flag to True, meaning less than 4f+1
        replication.rep = [ReplicaStructure(
            i,
            con_flag=True
        ) for i in range(4)] + [ReplicaStructure(5)]

        self.assertFalse(replication.conflict())

    def test_com_pref_states(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        replication.rep[0].set_rep_state([{"op": "add", "val": 0}])
        replication.rep[1].set_rep_state([{"op": "add", "val": 0}])
        replication.rep[2].set_rep_state([{"op": "add", "val": 1}])
        replication.rep[3].set_rep_state([{"op": "add", "val": 0}, {"op": "add", "val": 2}])
        replication.rep[4].set_rep_state([{"op": "add", "val": 3}])
        replication.rep[5].set_rep_state([{"op": "add", "val": 2}])

        self.assertEqual(replication.com_pref_states(2), [[{"op": "add", "val": 0}], [{"op": "add", "val": 0}]])
        self.assertEqual(replication.com_pref_states(3), [[{"op": "add", "val": 0}], [{"op": "add", "val": 0}],[{"op": "add", "val": 0}, {"op": "add", "val": 2}]])
        # no more than 3 processors have a common prefix
        self.assertEqual(replication.com_pref_states(4), [])

    def test_get_ds_state(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        replication.rep[0].set_rep_state([0])
        replication.rep[1].set_rep_state([0])
        replication.rep[2].set_rep_state([1])
        replication.rep[3].set_rep_state([0,2])
        replication.rep[4].set_rep_state([])
        replication.rep[5].set_rep_state([])

        replication.find_cons_state = MagicMock(return_value = ([0], []))
        self.assertEqual(replication.get_ds_state(), ([0], []))
        
        # Not enough processors with the state found in find_cons_state
        replication.rep[0].set_rep_state([2])
        replication.rep[1].set_rep_state([4])

        # TODO how check if get_ds_state is TEE? Might need to build a helper method for this
        self.assertEqual(replication.get_ds_state(), (-1, []))

    def test_double(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)
        
        replication.rep[0].set_req_q([
            {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}},
            {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PRE_PREP}}
        ])
        self.assertFalse(replication.double())

        # Adding a copy of message dummyRequest1 but with different sequence number,
        # double_message = {CLIENT_REQ: {CLIENT: 0}, VIEW: 1, SEQUENCE_NO: 2}
        double_message = Request(self.dummyRequest1.get_client_request(), 1, 2)
        replication.rep[replication.id].add_to_req_q(
            {REQUEST: double_message, STATUS: {ReplicationEnums.PRE_PREP}}
        )
        self.assertTrue(replication.double())

    def test_stale_req_seqn(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)

        # The replica has executed a request with sequence number within the threshold
        replication.last_exec = MagicMock(return_value = 1)
        self.assertFalse(replication.stale_req_seqn())

        # The replica has executed a request with sequence number outside the threshold
        replication.last_exec = MagicMock(return_value = sys.maxsize - SIGMA + 1)
        self.assertTrue(replication.stale_req_seqn())

    def test_unsup_req(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)

        # All processors have the same req_q, so there is no unsupported msg
        replication.rep = [ReplicaStructure(
            i,
            req_q=[
                {REQUEST: self.dummyRequest1, STATUS:{ReplicationEnums.PRE_PREP}}, 
                {REQUEST: self.dummyRequest2, STATUS:{ReplicationEnums.PRE_PREP}}
                ]
        ) for i in range(6)]

        self.assertFalse(replication.unsup_req())

        # Processor 0 has one unsupported request (dummyRequest2)
        # The rest does not have dummyRequest2 in their REQ_Q
        replication.rep = [ReplicaStructure(
            0,
            req_q=[
                {REQUEST: self.dummyRequest1, STATUS:{}},
                {REQUEST: self.dummyRequest2, STATUS: {}}
                ]
        )] + [ReplicaStructure(
            i,
            req_q=[
                {REQUEST: self.dummyRequest1, STATUS: {}}
                ]
        ) for i in range(1,6)]

        self.assertTrue(replication.unsup_req())

    def test_stale_rep(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        replication.stale_req_seqn = MagicMock(return_value = False)
        replication.double = MagicMock(return_value = False)
        replication.unsup_req = MagicMock(return_value = False)

        # Processor has a request in R_LOG that has enough processor in its X_SET
        replication.rep[replication.id].set_r_log([{REQUEST: self.dummyRequest2, X_SET:{1,2,3,4,5}}])
        self.assertFalse(replication.stale_rep())

        # Processor has a request in R_LOG that doesn't have enough processor in its X_SET
        replication.rep[replication.id].set_r_log([{REQUEST: self.dummyRequest2, X_SET:{3,4,5}}])
        self.assertTrue(replication.stale_rep())

        # The other methods should be called twice (calling the method twice in the test)
        self.assertEqual(replication.stale_req_seqn.call_count, 2)
        self.assertEqual(replication.double.call_count, 2)
        self.assertEqual(replication.unsup_req.call_count, 2)

    def test_known_pend_reqs(self):
        replication = ReplicationModule(0, Resolver(), 4, 1, 1)
        # Node 1-3 has both dummyRequests in pend queue
        # Node 4-5 have dummyRequest1 in pend queue
        # This means that known pending request are dummyRequest 1
        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request()
            ]
        ) for i in range(1,4)] + [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request()
                ]
        ) for i in range(4,6)]
        self.assertEqual(replication.known_pend_reqs(), [self.dummyRequest1.get_client_request()])

        # No known pending request found, only 3 processor has dummyRequest1
        replication.rep = [ReplicaStructure(
            0,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request()
                ]
        )] + [ReplicaStructure(
            i,
            pend_reqs=[self.dummyRequest1.get_client_request()
            ]
        ) for i in range(1,3)] + [ReplicaStructure(i) for i in range(3,6)]
        self.assertEqual(replication.known_pend_reqs(), [])

    def test_known_reqs(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        # Node 0 has both requests in request queue, the others have only request 1 with 
        # same status, should therefore return dummyRequest1
        replication.rep = [ReplicaStructure(
            0,
            req_q=[
                {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}},
                {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PREP}}
            ]
        )] + [ReplicaStructure(
            i,
            req_q=[
                {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}}
            ]
        ) for i in range(1,6)]
        
        self.assertEqual(
            replication.known_reqs({ReplicationEnums.PRE_PREP}),
            [{REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}}])

        # Asserting that the convertion to a set of the status works
        self.assertEqual(
            replication.known_reqs({ReplicationEnums.PRE_PREP}), 
            [{ REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP} }])

        # Node 0 has both requests in request queue, the others have only request 1 with 
        # other status, should therefore return empty
        replication.rep = [ReplicaStructure(
            0,
            req_q=[
                {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}},
                {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PREP}}
                ]
        )] + [ReplicaStructure(
            i,
            req_q=[
                {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.COMMIT}}
                ]
        ) for i in range(1,6)]
        
        self.assertEqual(
            replication.known_reqs({ReplicationEnums.COMMIT}), 
            [])

        # Should return dummyRequest1 eventhough they have different statuses,
        # since the other processor has this request with a status in the 
        # input stats (PRE_PREP, COMMIT)
        self.assertEqual(
            replication.known_reqs({ReplicationEnums.PRE_PREP, ReplicationEnums.COMMIT}),
            [{ REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP} }]
        )

    def test_delay(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)
        
        # Last execution will be within the threshold
        replication.last_common_exec = MagicMock(return_value = 3)
        replication.last_exec = MagicMock(return_value = 3)
        self.assertFalse(replication.delayed())

        # Last execution will be smaller than the threshold 
        replication.last_common_exec = MagicMock(return_value = 40)
        replication.last_exec = MagicMock(return_value = 3)
        self.assertTrue(replication.delayed())

    def test_exists_preprep_msg(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)
        # Primary is set to processor 1, with a PRE_PREP msg for dummyRequst 1
        replication.prim = 1
        replication.rep[1].set_req_q([
            { REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP} },
            { REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PREP} }
        ])

        self.assertTrue(replication.exists_preprep_msg(self.dummyRequest1.get_client_request(), 1))
        # No Pre_prep msg for dummyRequest2
        self.assertFalse(replication.exists_preprep_msg(self.dummyRequest2.get_client_request(), 1))
        # Node 0 is not prim, and there exists no Pre_prep msg in rep[0]
        self.assertFalse(replication.exists_preprep_msg(self.dummyRequest1.get_client_request(), 0))

    def test_unassigned_reqs(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)
        replication.rep[0].set_pend_reqs([self.dummyRequest1.get_client_request(), self.dummyRequest2.get_client_request()])

        # Both requests are unassigned
        replication.exists_preprep_msg = MagicMock(return_value = False)
        replication.known_reqs = MagicMock(return_value = [])
        self.assertEqual(replication.unassigned_reqs(), [self.dummyRequest1.get_client_request(), self.dummyRequest2.get_client_request()])
        calls = [
            call(self.dummyRequest1.get_client_request(), replication.rep[replication.id].get_prim()),
            call(self.dummyRequest2.get_client_request(), replication.rep[replication.id].get_prim())
        ]
        replication.exists_preprep_msg.assert_has_calls(calls)
       
        # Dummyrequest2 is in known_reqs with
        replication.known_reqs = MagicMock(return_value = [
            {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PREP}}
            ])
        self.assertEqual(replication.unassigned_reqs(), [self.dummyRequest1.get_client_request()])

        # There exists PRE_PREP msg for both of the requests
        replication.exists_preprep_msg = MagicMock(return_value = True)
        self.assertEqual(replication.unassigned_reqs(), [])

    def test_accept_req_preprep(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)

        replication.known_pend_reqs = MagicMock(return_value = [
            self.dummyRequest1.get_client_request(),
            self.dummyRequest2.get_client_request()
        ])
        replication.exists_preprep_msg = MagicMock(return_value = True)
        replication.last_exec = MagicMock(return_value = 0)
        replication.rep[replication.id].set_req_q([])
        replication.rep[self.dummyRequest1.get_view()].set_req_q([
            {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
            {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PREP}}])

        # The dummyRequest1 should be accepted
        self.assertTrue(replication.accept_req_preprep(self.dummyRequest1.get_client_request(), self.dummyRequest1.get_view()))

        # Request has a sequence number outside the threshold
        dummyRequest3 = Request(ClientRequest(2, None, None), 1, 10000)
        replication.known_pend_reqs = MagicMock(return_value = [dummyRequest3.get_client_request()])
        replication.rep[1].set_req_q([
            {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}},
            {REQUEST: dummyRequest3, STATUS: {ReplicationEnums.PREP}}
            ])
        self.assertFalse(replication.accept_req_preprep(dummyRequest3.get_client_request(), 1))

        # The input prim does not match any of the requests
        dummyRequest3 = Request(ClientRequest(2, None, None), 1, 1)

        replication.known_pend_reqs = MagicMock(return_value = [dummyRequest3.get_client_request()])
        replication.rep[replication.id].set_req_q([
            {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}},
            {REQUEST: dummyRequest3, STATUS: {ReplicationEnums.PREP}}
            ])
        self.assertFalse(replication.accept_req_preprep(dummyRequest3.get_client_request(), 1))
        
        # The dummyRequest1 (input) does not exists in known_pend_reqs
        replication.known_pend_reqs = MagicMock(return_value = [self.dummyRequest2.get_client_request()])
        self.assertFalse(replication.accept_req_preprep(self.dummyRequest1, self.dummyRequest1.get_view()))

        # Now the request already exists in REQ_Q (checks the logic of already_exists)
        replication.known_pend_reqs = MagicMock(return_value = [
            self.dummyRequest1.get_client_request(),
            self.dummyRequest2.get_client_request()
        ])
        replication.rep[replication.id].set_req_q([
            {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
        ])
        replication.rep[self.dummyRequest2.get_view()].set_req_q([
            {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
            {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
        ])
        self.assertFalse(replication.accept_req_preprep(self.dummyRequest1.get_client_request(), self.dummyRequest1.get_view()))
        
        # The dummyRequest2 on the other hand should be accepted
        self.assertTrue(replication.accept_req_preprep(self.dummyRequest2.get_client_request(), self.dummyRequest2.get_view()))

    def test_committed_set(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)

        # The other processor (1) has the dummyRequest2 in it's R_LOG but the msg-function does not
        # return any
        replication.rep[1].set_r_log([{REQUEST: self.dummyRequest2, X_SET: {5}}])
        replication.msg = MagicMock(return_value = [])
        self.assertEqual(replication.committed_set(self.dummyRequest2), {1})

        # The msg will return dummyRequest1 for both processors but it is not in R_LOG for any of the processors
        replication.rep[1].set_r_log([])
        replication.msg = MagicMock(return_value = [self.dummyRequest1])
        self.assertEqual(replication.committed_set(self.dummyRequest1),{0, 1})
        # No condition for dummyRequest2 will now be true
        self.assertEqual(replication.committed_set(self.dummyRequest2),set())


    # Interface functions

    def test_get_pend_reqs(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)

        # Should return the intersection of the two sets, meaning {2}
        replication.unassigned_reqs = MagicMock(return_value = {1,2})
        replication.known_pend_reqs = MagicMock(return_value = {2,3})
        replication.view_changed = False
        self.assertEqual(replication.get_pend_reqs(), {2})

    def test_rep_request_reset(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)

        # Should return false
        replication.need_flush = False
        self.assertFalse(replication.rep_request_reset())

        # Should change need_flush and return true
        replication.need_flush = True
        self.assertTrue(replication.rep_request_reset())
        self.assertFalse(replication.need_flush)

    def test_replica_flush(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)

        # Should change flush to True
        replication.flush = False
        replication.replica_flush()
        self.assertTrue(replication.flush)

    # Added functions
    def test_request_already_exists(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)
        dummyRequest3 = Request(ClientRequest(0, None, None), 2, 1)
        # The request does not already exist with a different status
        replication.rep[replication.id].set_req_q([
            {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}}
            ])
        self.assertFalse(replication.request_already_exists(self.dummyRequest2))
        
        # dummyRequest1 already exists with a different status
        replication.rep[replication.id].set_req_q([
            {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PREP}},
            {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PREP}}
            ])
        self.assertTrue(replication.request_already_exists(self.dummyRequest1))

        # dummyRequest3 is the same as dummyRequest2 beside the view -> found duplicate of sq_no and q
        replication.rep[replication.id].set_req_q([
            {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PREP}},
            {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PREP}},
            {REQUEST: dummyRequest3, STATUS: {ReplicationEnums.PREP}}])
        self.assertTrue(replication.request_already_exists(self.dummyRequest1))

    def test_prefixes(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)

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
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request()
                ],
            view_changed=True,
            req_q=[]
        ) for i in range(6)]
        # Pretend prim == replication.id (0)
        replication.resolver.execute = MagicMock(return_value = replication.id)
        replication.renew_reqs = Mock()
        replication.find_cons_state = MagicMock(return_value = ([], []))
        replication.last_exec = MagicMock(return_value = 0)
        # All nodes are in the processor set, because all has the same rep
        replication.act_as_prim_when_view_changed(replication.id)
        replication.find_cons_state.assert_called_once()
        replication.renew_reqs.assert_called_once_with({0,1,2,3,4,5})
        self.assertFalse(replication.rep[replication.id].get_view_changed())

        # Half of nodes has declared a view change, half has not
        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[self.dummyRequest1.get_client_request()],
            view_changed=True,
            req_q=[]
        ) for i in range(0, 3)] + [ReplicaStructure(
            i,
            pend_reqs=[self.dummyRequest1.get_client_request()],
            view_changed=False,
            req_q=[]
        ) for i in range(3, 6)]

        # Pretend prim == replication.id (0)
        replication.resolver.execute = MagicMock(return_value = replication.id)
        replication.renew_reqs = Mock()
        replication.find_cons_state = Mock()
        # Half of the nodes are in the set so it's less than 4f+1,
        #  methods should not be called and view_change = True
        replication.act_as_prim_when_view_changed(replication.id)
        replication.renew_reqs.assert_not_called()
        replication.find_cons_state.assert_not_called()
        self.assertTrue(replication.rep[replication.id].get_view_changed())

        # All has declared a view change but not all has 0 as prim
        replication.rep = [ReplicaStructure(
            i,
            req_q=[],
            pend_reqs=[self.dummyRequest1.get_client_request()],
            view_changed=True
        ) for i in range(6)]
        # Pretend prim == replication.id % 2 => half will say 0, half will say 1
        replication.resolver.execute = MagicMock(side_effect = lambda y, z, x: x % 2)
        replication.renew_reqs = Mock()
        replication.find_cons_state = Mock()
        # All nodes are in the processor set, because all has the same rep
        replication.act_as_prim_when_view_changed(replication.id)
        replication.find_cons_state.assert_not_called()
        replication.renew_reqs.assert_not_called()
        self.assertTrue(replication.rep[replication.id].get_view_changed())

    def test_updating_seq_num_when_prim(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)

        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[self.dummyRequest1.get_client_request()],
            req_q=[],
            view_changed=True
        ) for i in range(6)]
        # Pretend prim == replication.id (0)
        replication.resolver.execute = MagicMock(return_value = replication.id)
        replication.renew_reqs = Mock()
        replication.find_cons_state = MagicMock(return_value = ([], []))

        # Since req_q is empty, the sequence number should be the one from last_exex()
        replication.last_exec = MagicMock(return_value = 1)
        replication.act_as_prim_when_view_changed(replication.id)
        self.assertEqual(replication.rep[replication.id].get_seq_num(), 1)
        
        # Now there exists a request in req_q that has a higher sequence number (2) than
        # last executed (1)
        replication.rep[replication.id] = ReplicaStructure(
            replication.id,
            pend_reqs=[
                self.dummyRequest1.get_client_request()
                ],
            req_q=[
                {REQUEST: self.dummyRequest2, STATUS:{ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                ],
            view_changed=True
        )
        replication.act_as_prim_when_view_changed(replication.id)
        self.assertEqual(replication.rep[replication.id].get_seq_num(), 2)

    def test_act_as_nonprim_when_view_changed(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)

        # Prim will be node 5, has a different replica strucutre
        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request()
                ],
            view_changed=True,
            prim=5
        ) for i in range(5)] + [ReplicaStructure(
            5,
            pend_reqs=[
                self.dummyRequest2.get_client_request()
                ],
            prim=5
        )]
        # Everybody has 5 as prim and check_new_v_state returns True
        replication.resolver.execute = MagicMock(return_value = 5)
        replication.check_new_v_state = MagicMock(return_value = True)
        replication.act_as_nonprim_when_view_changed(5)

        self.assertFalse(replication.rep[replication.id].get_view_changed())
        self.assertEqual(replication.rep[replication.id].get_pend_reqs(), [self.dummyRequest2.get_client_request()])

        # The replica should not accept node 5's rep state
        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request()
                ],
            view_changed=True
        ) for i in range(5)] + [ReplicaStructure(
            5,
            pend_reqs=[
                self.dummyRequest2.get_client_request()
                ]
        )]
        # Should not accept node 5's rep and view Change should stay true
        replication.check_new_v_state = MagicMock(return_value = False)
        replication.act_as_nonprim_when_view_changed(5)
        self.assertTrue(replication.rep[replication.id].get_view_changed())

        self.assertNotEqual(replication.rep[replication.id], ReplicaStructure(
            replication.id,
            pend_reqs=[self.dummyRequest2.get_client_request()]
        ))

        # Prim will be node 1, has a different replica structure
        replication.rep = [ReplicaStructure(
            0,
            pend_reqs=[
                self.dummyRequest2.get_client_request()
                ],
            view_changed=True
        )] + [ReplicaStructure(
            1,
            pend_reqs=[
                self.dummyRequest1.get_client_request()
                ]
        )] + [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest2.get_client_request()
                ],
            view_changed=True
        ) for i in range(2,6)]
        # less than 4f+1 has 0 as prim but check_new_v_state returns True
        replication.resolver.execute = MagicMock(side_effect = lambda y, z, x: x % 2)
        replication.check_new_v_state = MagicMock(return_vale = True)
        replication.act_as_nonprim_when_view_changed(1)

        self.assertTrue(replication.rep[replication.id].get_view_changed())
        self.assertNotEqual(replication.rep[replication.id], ReplicaStructure(
            replication.id,
            pend_reqs=[self.dummyRequest1.get_client_request()]
        ))

    # def test_reqs_to_prep(self):
    #     replication = ReplicationModule(0, Resolver(), 6, 1, 1)
    #     # DummyRequest1 exists in unassigned_reqs
    #     replication.unassigned_reqs = MagicMock(return_value = [self.dummyRequest1])
    #     self.assertFalse(replication.reqs_to_prep(self.dummyRequest1))

    #     # DummyRequest1 does not exist in unassigned_reqs but in rep[REQ_Q]
    #     replication.unassigned_reqs = MagicMock(return_value = [])
    #     replication.rep[replication.id].set_req_q([
    #         {REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP}
    #         ])
    #     self.assertFalse(replication.reqs_to_prep(self.dummyRequest1))

    #     # DummyRequest2 is accepted
    #     replication.accept_req_preprep = MagicMock(return_value = True)
    #     self.assertTrue(replication.reqs_to_prep(self.dummyRequest2))

    def test_commit(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 2)
        replication.rep = [ReplicaStructure(i, rep_state=[]) for i in range(6)]
        replication.rep[replication.id] = ReplicaStructure(
            replication.id,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request()
            ],
            req_q=[
                {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP, ReplicationEnums.COMMIT}}
            ],
            r_log=[],
            last_req=[None for i in range(2)],
            view_changed=True,
            rep_state=[]
        )

        # Commit should removed dummyRequest 1 from pend_reqs and req_q and add to last_req and R_log
        replication.commit({REQUEST: self.dummyRequest1, X_SET: {0,1,2,3,4,5}})
        target = ReplicaStructure(
            replication.id,
            rep_state=[1],
            last_req=[{REQUEST: self.dummyRequest1, REPLY: [1]}, None],
            r_log=[
                {REQUEST: self.dummyRequest1, X_SET: {0,1,2,3,4,5}}
            ],
            req_q=[],
            pend_reqs=[
                self.dummyRequest2.get_client_request()
            ],
            view_changed=True
        )

        self.assertEqual(replication.rep[replication.id], target)

    def test_while_check_for_view_change(self):
        # Line 1-3
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = Mock()
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = False)
        replication.last_exec = Mock()
        replication.committed_set = MagicMock(return_value = [])
        replication.reqs_to_prep = Mock()
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()
        replication.flush_local = Mock()
        replication.prefixes = MagicMock(return_value = True)

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        replication.find_cons_state = MagicMock(return_value = ([], []))
        replication.get_ds_state = MagicMock(return_value = [])
        replication.known_pend_reqs = MagicMock(return_value = [])

        # The resolver should return the current view (0)
        replication.resolver.execute = MagicMock(side_effect = lambda y, func, x=-1 : self.get_0_as_view(func))
        replication.run()
        # Node started with DEF_STATE, should have changed the following parameters
        self.assertEqual(replication.rep[replication.id].get_prim(), 0)
        self.assertFalse(replication.rep[replication.id].get_view_changed())

        # The view change should be set to True, our prim is different from what algo 2 
        # returns
        replication.rep = [ReplicaStructure(
            i,
            prim=5
        ) for i in range(6)]
        replication.run()

        self.assertEqual(replication.rep[replication.id].get_prim(), 0)
        self.assertTrue(replication.rep[replication.id].get_view_changed())

    def test_while_view_change_occur_check_calls(self):
        # Line 4-8
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
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

        replication.find_cons_state = MagicMock(return_value = ([], []))
        replication.get_ds_state = MagicMock(return_value = [])
        replication.known_pend_reqs = MagicMock(return_value = [])

        # Used to set prim of self.id
        # Node 0 is prim
        replication.resolver.execute = MagicMock(return_value = 0)
        replication.rep = [ReplicaStructure(i, view_changed=True, prim=0) for i in range(6)]

        replication.run()
        replication.act_as_prim_when_view_changed.assert_called_once()

        replication.rep = [ReplicaStructure(i, view_changed=True, prim= 5) for i in range(5)] \
                            + [ReplicaStructure(6, prim=5)]

        # Node 0 is NOT primary anymore, node 5 is
        replication.resolver.execute = MagicMock(return_value = 5)
        replication.run()
        replication.act_as_nonprim_when_view_changed.assert_called_once()

    def test_while_finding_consolidated_state(self):
        # Line 9-11
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = Mock()
        replication.last_exec = Mock()
        replication.unassigned_reqs = Mock()
        replication.committed_set = MagicMock(return_value = [])
        replication.reqs_to_prep = Mock()
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        # These functions are not used for the current case of test
        replication.get_ds_state = MagicMock(return_value = ([], []))
        replication.resolver.execute = MagicMock(return_value = -1)
        replication.known_pend_reqs = MagicMock(return_value = [])

        # The consolidated state is mock_rep_state
        mock_rep_state = [1,2]
        mock_r_log = [
            {REQUEST: self.dummyRequest1, REPLY: [1]},
            {REQUEST: self.dummyRequest2, REPLY: [1,2]}
        ]
        replication.find_cons_state = MagicMock(return_value = (mock_rep_state, mock_r_log))
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = False)

        # Node 0 has DEF_STATE, should "adopt" mock_rep_state
        replication.run()
        self.assertFalse(replication.rep[replication.id].get_con_flag())
        self.assertEqual(replication.rep[replication.id].get_rep_state(), mock_rep_state)
        self.assertEqual(replication.rep[replication.id].get_r_log(), mock_r_log)

        # Node 0 REP_STATE is not a prefix of mock_rep_state and should adopt
        replication.rep = [ReplicaStructure(
            i,
            rep_state=[7],
            prim=4
        ) for i in range(5)]

        replication.run()
        self.assertEqual(replication.rep[replication.id].get_rep_state(), mock_rep_state)
        self.assertEqual(replication.rep[replication.id].get_r_log(), mock_r_log)

    def test_while_assigning_y_to_x(self):
        # Line 9-11
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = Mock()
        replication.last_exec = Mock()
        replication.unassigned_reqs = Mock()
        replication.committed_set = MagicMock(return_value = [])
        replication.reqs_to_prep = Mock()
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        # These functions are not used for the current case of test

        replication.resolver.execute = MagicMock(return_value = -1)
        replication.known_pend_reqs = MagicMock(return_value = [])

        # The consolidated state is not found
        replication.find_cons_state = MagicMock(return_value = (-1, []))
        # Get DS_state on the other hand returns a rep_state
        mock_rep_state = [1,2]
        mock_r_log = [
            {REQUEST: self.dummyRequest1, REPLY: [1]},
            {REQUEST: self.dummyRequest2, REPLY: [1,2]}
        ]
        replication.get_ds_state = MagicMock(return_value = (mock_rep_state, mock_r_log))
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = False)

        # Node 0 has DEF_STATE, should "adopt" mock_rep_state
        replication.run()
        self.assertFalse(replication.rep[replication.id].get_con_flag())
        self.assertEqual(replication.rep[replication.id].get_rep_state(), mock_rep_state)
        self.assertEqual(replication.rep[replication.id].get_r_log(), mock_r_log)

        # Node 0 REP_STATE is not a prefix of mock_rep_state and should adopt
        replication.rep = [ReplicaStructure(
            i,
            rep_state=[7],
            prim=4
        ) for i in range(5)]

        replication.run()
        self.assertEqual(replication.rep[replication.id].get_rep_state(), mock_rep_state)
        self.assertEqual(replication.rep[replication.id].get_r_log(), mock_r_log)

    def test_while_reset_cases(self):
        # Lines 12-13
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
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
        replication.find_cons_state = MagicMock(return_value = ([], []))
        replication.get_ds_state = MagicMock(return_value = [])
        replication.resolver.execute = MagicMock(return_value = 0)
        replication.known_pend_reqs = MagicMock(return_value = [])

        # Specific mock-calls for this case test
        replication.stale_rep = MagicMock(return_value = True)
        replication.conflict = MagicMock(return_value = False)

        # The node does not have DEF_STATE
        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request()
                ],
            view_changed=True,
            prim=2
        ) for i in range(6)]

        # The node should flush it's rep, meaning having DEF_STATE
        replication.need_flush = False
        replication.run()
        self.assertTrue(replication.need_flush)
        replication.flush_local.assert_called_once()
        self.assertTrue(replication.rep[replication.id].is_tee())

        # Specific mock-calls for this case test
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = True)

        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request()
                ],
            view_changed=True,
            prim=2
        ) for i in range(6)]

        # The node should flush it's rep, meaning having DEF_STATE
        replication.need_flush = False
        replication.flush_local = Mock()
        replication.run()
        self.assertTrue(replication.need_flush)
        self.assertTrue(replication.rep[replication.id].is_tee())
        replication.flush_local.assert_called_once()

        # Just testing flush = True -> flush_local called
        replication.flush = True
        replication.flush_local = Mock()
        replication.run()
        # Being called twice, once on line 12 and once in line 13
        self.assertEqual(replication.flush_local.call_count, 2)

    def test_while_assigning_pre_prep_as_prim(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = MagicMock(return_value = False)
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = False)
        replication.known_pend_reqs = Mock()
        
        replication.committed_set = MagicMock(return_value = [])
        replication.reqs_to_prep = Mock()
        replication.commit = Mock()
        replication.known_reqs = MagicMock(return_value = [])
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        replication.find_cons_state = MagicMock(return_value = ([], []))
        replication.get_ds_state = MagicMock(return_value = ([], []))
        replication.resolver.execute = MagicMock(side_effect = lambda y, func, x=-1 : self.get_0_as_view(func))
        replication.known_pend_reqs = MagicMock(return_value = [])
        replication.last_exec = MagicMock(return_value = 2)

        unassigned_req1 = ClientRequest(0, None, None)
        unassigned_req2 = ClientRequest(1, None, None)
        replication.rep[replication.id] = ReplicaStructure(
            replication.id,
            pend_reqs=[unassigned_req1, unassigned_req2],
            prim=0,
            seq_num=2,
            req_q=[]
        )
        replication.run()

        assigned_req1 = Request(unassigned_req1, 0, 3)
        assigned_req2 = Request(unassigned_req2, 0, 4)

        # Pending request: create dummy "real" requests of the client request in pend-reqs
        # The pending requests are being assigned sequencial sequence numbers and
        # added to REQ_QUEUE
        self.assertEqual(replication.rep[replication.id].get_req_q(),
        [{REQUEST: assigned_req1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}, 
        {REQUEST: assigned_req2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}])

    def test_while_assigning_pre_prep_as_non_prim(self):
        replication = ReplicationModule(1, Resolver(), 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = MagicMock(return_value = False)
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = False)
        replication.unassigned_reqs = MagicMock(return_value = [])
        replication.committed_set = MagicMock(return_value = [])
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        replication.find_cons_state = MagicMock(return_value = ([], []))
        replication.get_ds_state = MagicMock(return_value = [])
        replication.resolver.execute = MagicMock(side_effect = lambda y, func, x=-1 : self.get_0_as_view(func))
        replication.last_exec = MagicMock(return_value = 2)
        replication.seq_n = 2

        # Request that the prim has send with PRE_prep and Prep
        assigned_req1 = Request(ClientRequest(0, None, None), 0, 3)
        assigned_req2 = Request(ClientRequest(1, None, None), 0, 4)

        replication.rep = [ReplicaStructure(
            0,
            pend_reqs=[
                assigned_req1.get_client_request(),
                assigned_req2.get_client_request()],
            req_q =[
                {REQUEST: assigned_req1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
                {REQUEST: assigned_req2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                ],
            prim=0
        )] + [ReplicaStructure(
            i,
            pend_reqs=[
                assigned_req1.get_client_request(),
                assigned_req2.get_client_request()],
            req_q=[],
            prim=0
        ) for i in range(1,6)]
        replication.run()

        # The pending requests are being assigned sequencial sequence numbers and
        # added to REQ_QUEUE
        self.assertEqual(replication.rep[replication.id].get_req_q(),
        [{REQUEST: assigned_req1, STATUS: {ReplicationEnums.PRE_PREP}}, 
        {REQUEST: assigned_req2, STATUS: {ReplicationEnums.PRE_PREP}}])

    def test_while_assigning_prep_as_non_prim(self):
        replication = ReplicationModule(1, Resolver(), 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = MagicMock(return_value = False)
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = False)
        replication.unassigned_reqs = MagicMock(return_value = [])
        replication.committed_set = MagicMock(return_value = [])
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()
        #replication.accept_req_preprep = MagicMock(return_value = True)

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        replication.find_cons_state = MagicMock(return_value = ([], []))
        replication.get_ds_state = MagicMock(return_value = [])
        replication.resolver.execute = MagicMock(side_effect = lambda y, func, x=-1 : self.get_0_as_view(func))
        replication.last_exec = MagicMock(return_value = 2)
        replication.seq_n = 2

        # Request that the prim has send with PRE_prep and Prep
        assigned_req1 = Request(ClientRequest(0, None, None), 0, 3)
        assigned_req2 = Request(ClientRequest(1, None, None), 0, 4)

        replication.rep = [ReplicaStructure(
            0,
            r_log=[],
            pend_reqs=[
                assigned_req1.get_client_request(),
                assigned_req2.get_client_request()],
            req_q =[
                {REQUEST: assigned_req1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
                {REQUEST: assigned_req2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                ],
            prim=0
        )] + [ReplicaStructure(
            i,
            r_log=[],
            pend_reqs=[
                assigned_req1.get_client_request(),
                assigned_req2.get_client_request()],
            req_q=[{REQUEST: assigned_req1, STATUS: {ReplicationEnums.PRE_PREP}},
                {REQUEST: assigned_req2, STATUS: {ReplicationEnums.PRE_PREP}}],
            prim=0
        ) for i in range(1,6)]
        replication.run()
        # The status of the requests should be updated to both PRE_PREP and PREP
        self.assertEqual(replication.rep[replication.id].get_req_q(),
        [{REQUEST: assigned_req1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}, 
         {REQUEST: assigned_req2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}])

    def test_while_committing_to_request(self):
        # line 22
        replication = ReplicationModule(1, Resolver(), 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = MagicMock(return_value = False)
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = False)
        replication.unassigned_reqs = MagicMock(return_value = [])
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()
        replication.accept_req_preprep = MagicMock(return_value = True)
        replication.known_pend_reqs = MagicMock(return_value =[])

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        replication.find_cons_state = MagicMock(return_value = ([], []))
        replication.get_ds_state = MagicMock(return_value = [])
        replication.committed_set = MagicMock(return_value = {0,1,2,3,4,5})
        replication.resolver.execute = MagicMock(side_effect = lambda y, func, x=-1 : self.get_0_as_view(func))
        replication.last_exec = MagicMock(return_value = 2)
        replication.seq_n = 2
        assigned_req1 = Request(ClientRequest(0, None, None), 0, 3)
        assigned_req2 = Request(ClientRequest(1, None, None), 0, 4)

        req_q = [
            {REQUEST: assigned_req1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
            {REQUEST: assigned_req2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}]
        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[
                assigned_req1.get_client_request(),
                assigned_req2.get_client_request()],
            req_q=req_q,
            prim=0
        ) for i in range(6)]

        replication.run()

        # The pending assignment should be removed from pend_reqs
        self.assertEqual(replication.rep[replication.id].get_pend_reqs(), [])
        # Commit should have been added to Status for each of the request
        self.assertEqual(replication.rep[replication.id].get_req_q(), [
            {REQUEST: assigned_req1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP, ReplicationEnums.COMMIT}},
            {REQUEST: assigned_req2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP, ReplicationEnums.COMMIT}}
        ])

    def test_while_actually_comitting_request(self):
        # line 23-25
        replication = ReplicationModule(1, Resolver(), 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = MagicMock(return_value = False)
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = False)
        replication.unassigned_reqs = MagicMock(return_value = [])
        replication.commit = Mock()
        replication.act_as_nonprim_when_view_changed = Mock()
        replication.act_as_prim_when_view_changed = Mock()
        replication.send_msg = Mock()
        replication.accept_req_preprep = MagicMock(return_value = True)
        replication.known_pend_reqs = MagicMock(return_value =[])

        # If not returning arrays, it returns an Mock-object and tests don't pass at all
        replication.find_cons_state = MagicMock(return_value = ([], []))
        replication.get_ds_state = MagicMock(return_value = [])
        replication.committed_set = MagicMock(return_value = {0,1,2,3,4,5})
        replication.resolver.execute = MagicMock(side_effect = lambda y, func, x=-1 : self.get_0_as_view(func))
        replication.last_exec = MagicMock(return_value = 2)
        assigned_req1 = Request(ClientRequest(0, None, None), 0, 3)
        assigned_req2 = Request(ClientRequest(1, None, None), 0, 4)

        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[
                assigned_req1.get_client_request(),
                assigned_req2.get_client_request()
                ],
            req_q=[
                {REQUEST: assigned_req1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP, ReplicationEnums.COMMIT}},
                {REQUEST: assigned_req2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP, ReplicationEnums.COMMIT}}
                ],
            prim=0
        ) for i in range(6)]
        replication.rep[replication.id].set_seq_num(2)

        replication.run()
        # Commit should be called with only assigned_req1 (since lastExec() returns 2)
        replication.commit.assert_called_once_with({REQUEST: {REQUEST: assigned_req1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP, ReplicationEnums.COMMIT}},
                                                    X_SET: {0,1,2,3,4,5}})

    def template_for_while_true(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        replication.run_forever = False
        # All functions called in while must be mocked:

        replication.com_pref_states = Mock()
        replication.delayed = Mock()
        replication.stale_rep = MagicMock(return_value = False)
        replication.conflict = MagicMock(return_value = False)
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
        replication.find_cons_state = MagicMock(return_value = ([], []))
        replication.get_ds_state = MagicMock(return_value = [])
        replication.resolver.execute = MagicMock(return_value = 0)

        replication.rep = [ReplicaStructure(i) for i in range(6)]
    
    # validates applying requests
    def test_apply(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        state = []
        target_state = [0, 1, 2, 3, 4]

        # append 1..5
        for i in range(5):
            op = Operation(OperationEnums.APPEND, i)
            client_req = ClientRequest(0, None, op)
            req = Request(client_req, 0, i)
            replication.apply(req)

        # no-op
        op = Operation(OperationEnums.NO_OP)
        client_req = ClientRequest(0, None, op)
        req = Request(client_req, 0, 5)
        replication.apply(req)

        self.assertEqual(replication.rep[replication.id].get_rep_state(), target_state)

    def test_accept_req_prep(self):
        # Indirect checks prep_request_already_exists-method
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        req_q = [
            {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
            {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}]
        replication.rep = [ReplicaStructure(
            0,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request()],
            prim=1,
            req_q = [
                {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}},
                {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                ]
            )]+ [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request()
                ],
            req_q=req_q,
            prim=1
        ) for i in range(1,6)]
        # dummyRequest1 is OK
        self.assertTrue(replication.accept_req_prep(self.dummyRequest1, 0))
        # dummyRequest2 does already exist with PREP in processor's req_Q
        self.assertFalse(replication.accept_req_prep(self.dummyRequest2, 0))


    def test_renew_reqs(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        request3 = ClientRequest(0, None, None)
        req_q = [
                {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}},
                {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                ]

        # The first 3 processors has an extra clientRequest (request3)
        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request(),
                request3],
            prim=0,
            req_q = req_q,
            seq_num = 2
            ) for i in range(3)]+ [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request()
                ],
            req_q=req_q,
            prim=0
        ) for i in range(3,6)]

        replication.renew_reqs({0,1,2,3,4,5})
        # Request3 should be discarged
        self.assertEqual(replication.rep[replication.id].get_pend_reqs(),
            [self.dummyRequest1.get_client_request(),
            self.dummyRequest2.get_client_request()])
        # dummyRequest1 need a new Pre_prep message with the new primary as view
        # dummyRequest1 has default view = 1, and sequence number 1,
        # should now be updated
        self.maxDiff = None
        newRequest = Request(ClientRequest(0, None, Operation(
            OperationEnums.APPEND, 1
        )), 0, 3)
        self.assertEqual(replication.rep[replication.id].get_req_q(),
            [
            {REQUEST: newRequest, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
            {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                ])

    def test_check_new_v_state(self):
        # I'm 1 and prim = 0
        replication = ReplicationModule(1, Resolver(), 6, 1, 1)
        replication.check_new_state_and_r_log = MagicMock(return_value = True)
        newRequest = Request(ClientRequest(0, None, Operation(
            OperationEnums.APPEND, 1
        )), 0, 3)
        request3 = ClientRequest(0, None, None)
        req_q = [
                {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}},
                {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                ]
        
        prim_req_q = [
                    {REQUEST: newRequest, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
                    {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                    ]
        # Node 0 has updated it's replica structure and I will check it
        # It is Correct
        replication.rep = [ReplicaStructure(
            0,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request(),
                ],
            prim=0,
            req_q = prim_req_q,
            seq_num = 2
            )]+ [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request()
                ],
            req_q=req_q,
            prim=0
        ) for i in range(1,6)]

        self.assertTrue(replication.check_new_v_state(0))

        # It is Faulty, pending reqs has an extra request.
        replication.rep = [ReplicaStructure(
            0,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request(),
                request3],
            prim=0,
            req_q = prim_req_q,
            seq_num = 2
            )]+ [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request()
                ],
            req_q=req_q,
            prim=0
        ) for i in range(1,6)]

        self.assertFalse(replication.check_new_v_state(0))

    def test_check_new_v_state_false_req_q(self):
        # I'm 1 and prim = 0
        replication = ReplicationModule(1, Resolver(), 6, 1, 1)
        replication.check_new_state_and_r_log = MagicMock(return_value = True)
        newRequest = Request(ClientRequest(0, None, Operation(
            OperationEnums.APPEND, 1
        )), 0, 3)
        request3 = ClientRequest(0, None, None)
        req_q = [
                #{REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP}},
                {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                ]
        # Primary has a newRequest that does not exists at the other processors req_q
        prim_req_q = [
                    {REQUEST: newRequest, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
                    {REQUEST: self.dummyRequest2, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                    ]
        # Node 0 has updated it's replica structure and I will check it
        # It is Correct
        replication.rep = [ReplicaStructure(
            0,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request(),
                ],
            prim=0,
            req_q = prim_req_q,
            seq_num = 2
            )]+ [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                self.dummyRequest2.get_client_request()
                ],
            req_q=req_q,
            prim=0
        ) for i in range(1,6)]

        self.assertFalse(replication.check_new_v_state(0))

    # Functions used to mock execute at resolver
    def get_0_as_view(self, func):
        if (func == Function.ALLOW_SERVICE):
            return True
        elif (func == Function.NO_VIEW_CHANGE):
            return True
        else:
            return 0

    # Added functions after implementing find_cons_state

    def test_is_prefix_of(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)

        # Basic examples
        log_A = [1,2,3]
        log_B = [1,2]
        self.assertFalse(replication.is_prefix_of(log_A, log_B))
        self.assertTrue(replication.is_prefix_of(log_B, log_A))

        log_B = [1,2,5]
        self.assertFalse(replication.is_prefix_of(log_B, log_A))
        
        log_A = []
        self.assertTrue(replication.is_prefix_of(log_A, log_B))

        # Examples with dcts
        log_A = [{REQUEST: self.dummyRequest1, X_SET:{2}}]
        log_B = [{REQUEST: self.dummyRequest1, X_SET:{2}}, 
                {REQUEST: self.dummyRequest2, X_SET:{1,3}}, 
                ]
        self.assertTrue(replication.is_prefix_of(log_A, log_B))
        self.assertFalse(replication.is_prefix_of(log_B, log_A))
        
        log_A = [{REQUEST: self.dummyRequest1, X_SET:{2,4}}]
        log_B = [{REQUEST: self.dummyRequest1, X_SET:{2}}, 
                {REQUEST: self.dummyRequest2, X_SET:{1,3}}, 
                ]
        self.assertFalse(replication.is_prefix_of(log_A, log_B))

    def test_find_prefix(self):
        replication = ReplicationModule(0, Resolver(), 2, 0, 1)

        # Basic examples
        log_A = [1,2,3]
        log_B = [1,2]
        self.assertEqual(replication.find_prefix([log_A, log_B]), [1,2])
        self.assertEqual(replication.find_prefix([log_B, log_A]), [1,2])

        log_B = [1,2,5]
        self.assertEqual(replication.find_prefix([log_B, log_A]), [1,2])
        
        log_A = []
        self.assertEqual(replication.find_prefix([log_A, log_B]), [])

        log_A = [2,5]
        self.assertEqual(replication.find_prefix([log_A, log_B]), [])

    def test_produce_dummy_req(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        target_request = Request(
            ClientRequest(-1, None, Operation(
                OperationEnums.NO_OP
            )),
            0,
            2)
        self.assertEqual(replication.produce_dummy_req(2),
            {
            REQUEST: target_request,
            STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PRE_PREP}
            })

    def test_req_with_seq_num_in_req_q(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        seq_num_jump_request = Request(ClientRequest(0, None, Operation(
            OperationEnums.APPEND, 1
        )), 2, 4)
        replication.rep[replication.id].set_req_q([
            {REQUEST: self.dummyRequest1,
            STATUS: {ReplicationEnums.PRE_PREP}
            },
            {REQUEST: self.dummyRequest2,
            STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}
            },
            {REQUEST: seq_num_jump_request, 
            STATUS:{ReplicationEnums.PRE_PREP, ReplicationEnums.PREP} }
            ])
        self.assertTrue(replication.req_with_seq_num_in_req_q(1))
        self.assertTrue(replication.req_with_seq_num_in_req_q(2))
        self.assertFalse(replication.req_with_seq_num_in_req_q(3))
        self.assertTrue(replication.req_with_seq_num_in_req_q(4))

    def test_check_new_state_and_r_log(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        # Let prim == 1
        replication.rep = [ReplicaStructure(
            i,
            rep_state = [1,2,3],
            r_log = [],
            prim=1
        ) for i in range(6)]

        # Change replica structure of primary
        prim_r_log = [
            {REQUEST: self.dummyRequest1, REPLY: [1]},
            {REQUEST: self.dummyRequest2, REPLY: [1,2]}]

        replication.rep[1].set_rep_state([1,2])
        replication.rep[1].set_r_log(prim_r_log)
        self.assertTrue(replication.check_new_state_and_r_log(1))

        # Now the r_log does not comply with the given new state
        prim_r_log = [
            {REQUEST: self.dummyRequest1, REPLY: [1]},
            {REQUEST: self.dummyRequest1, REPLY: [1,1]}]
        replication.rep[1].set_r_log(prim_r_log)
        self.assertFalse(replication.check_new_state_and_r_log(1))

        # The replica state of the primary is not a prefix of the others
        replication.rep[1].set_rep_state([1,4])
        self.assertFalse(replication.check_new_state_and_r_log(1))

    def test_find_cons_state(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        # Let prim == 1
        r_log_entries = [
            {REQUEST: self.dummyRequest1, REPLY: [1]},
            {REQUEST: self.dummyRequest2, REPLY: [1,2]}]

        # all replicas has the same state and r_log
        replication.rep = [ReplicaStructure(
            i,
            rep_state = [1,2],
            r_log = r_log_entries,
            prim=1
        ) for i in range(6)]

        processor_states = [[1,2] for i in range(6)]

        target = ([1,2], r_log_entries)
        self.assertEqual(replication.find_cons_state(processor_states), target)

        # Empty set should return "TEE"
        self.assertEqual(replication.find_cons_state([]), (-1, []))

        # Empty R_log should return "TEE"
        # Their r_log does not match the common prefix     
        replication.rep = [ReplicaStructure(
            i,
            rep_state = [1,2],
            r_log = [{REQUEST: self.dummyRequest1, REPLY: [1]}],
            prim=1
        ) for i in range(6)]
        self.assertEqual(replication.find_cons_state(processor_states), (-1, []))   

        # Empty prefix_state should return "TEE"
        # Nodes don't have a prefix in common
        replication.rep = [ReplicaStructure(
            i,
            rep_state = [1,2],
            r_log = r_log_entries,
            prim=1
        ) for i in range(3)] + [ReplicaStructure(
            i,
            rep_state = [2,4],
            r_log = r_log_entries,
            prim=1
        ) for i in range(3,6)]

        processor_states = [[1,2] for i in range(3)] + [[2,4] for i in range(3,6)]
        self.assertEqual(replication.find_cons_state(processor_states), (-1, []))



    def test_check_new_v_state_including_dummy_request(self):
        # Primary is 0 and I'm 1
        replication = ReplicationModule(1, Resolver(), 6, 1, 1)
        replication.check_new_state_and_r_log = MagicMock(return_value = True)

        # dummyRequest1 has seq_no 1
        # seq_num_jump_request has 3
        # => We need a dummyRequest with seq_num = 2
        dummy_request = Request(
            ClientRequest(-1, None, Operation(
                OperationEnums.NO_OP
            )),
            0, 2)
        # This is in the old view, should be assigned 
        seq_num_jump_request = Request(ClientRequest(0, None, Operation(
            OperationEnums.APPEND, 1
        )), 2, 3)
        req_q = [
                {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
                {REQUEST: seq_num_jump_request, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                ]
        # Primary adds the dummyRequest
        prim_req_q = [
                    {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
                    {REQUEST: seq_num_jump_request, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
                    {REQUEST: dummy_request, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PRE_PREP}
            }]
        # Node 0 has updated it's replica structure and I will check it
        # It is Correct
        replication.rep = [ReplicaStructure(
            0,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                seq_num_jump_request.get_client_request(),
                ],
            prim=0,
            req_q = prim_req_q,
            seq_num = 1
            )]+ [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                seq_num_jump_request.get_client_request(),
                ],
            req_q=req_q,
            prim=0
        ) for i in range(1,6)]

        self.assertTrue(replication.check_new_v_state(0))

    def test_act_as_prim_when_view_changed_produce_dummy(self):
        replication = ReplicationModule(0, Resolver(), 6, 1, 1)
        # Pretend prim == replication.id (0)
        replication.resolver.execute = MagicMock(return_value = 0)
        replication.renew_reqs = Mock()
        replication.find_cons_state = MagicMock(return_value = ([], []))
        replication.last_exec= MagicMock(return_value = 0)
        
        dummy_request = Request(
            ClientRequest(-1, None, Operation(
                OperationEnums.NO_OP
            )),
            0, 2)

        replication.produce_dummy_req = MagicMock(return_value = {REQUEST: dummy_request,
                                STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}})
        seq_num_jump_request = Request(ClientRequest(0, None, Operation(
            OperationEnums.APPEND, 1
        )), 2, 3)
        req_q = [
                {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
                {REQUEST: seq_num_jump_request, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
                ]
        replication.rep = [ReplicaStructure(
            i,
            pend_reqs=[
                self.dummyRequest1.get_client_request(),
                seq_num_jump_request.get_client_request(),
                ],
            prim=0,
            req_q = req_q,
            seq_num = 1,
            view_changed=True
            ) for i in range(6)]

        # Half of the nodes are in the set so it's less than 4f+1,
        #  methods should not be called and view_change = True
        replication.act_as_prim_when_view_changed(0)
        self.assertEqual(replication.rep[replication.id].get_req_q(),
        [
            {REQUEST: self.dummyRequest1, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
            {REQUEST: seq_num_jump_request, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}},
            {REQUEST: dummy_request, STATUS: {ReplicationEnums.PRE_PREP, ReplicationEnums.PREP}}
            ])
        replication.renew_reqs.assert_called_once()
        self.assertFalse(replication.rep[replication.id].get_view_changed())

