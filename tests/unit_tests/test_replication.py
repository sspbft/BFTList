import unittest
from unittest.mock import Mock, MagicMock
import sys
from resolve.resolver import Resolver
from modules.replication.module import ReplicationModule
from resolve.enums import Function, Module
from modules.enums import ReplicationEnums
from modules.constants import (REP_STATE, R_LOG, PEND_REQS, REQ_Q,
                               LAST_REQ, CON_FLAG, VIEW_CHANGE,
                               REQUEST, SEQUENCE_NO, STATUS, VIEW, X_SET, CLIENT_REQ) # REPLY

class TestReplicationModule(unittest.TestCase):

    def setUp(self):
        self.resolver = Resolver()
        self.dummyRequest1 = {CLIENT_REQ: {}, VIEW: 1, SEQUENCE_NO: 1}
        self.dummyRequest2 = {CLIENT_REQ: {}, VIEW: 1, SEQUENCE_NO: 2}
    
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
        replication.rep[1] = {
             REP_STATE: {},
             R_LOG: [],
             PEND_REQS: [],
             REQ_Q: [
                 {REQUEST: self.dummyRequest1, STATUS: ReplicationEnums.PRE_PREP},
                 {REQUEST: self.dummyRequest2, STATUS: ReplicationEnums.PREP}],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False}

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
                    {REQUEST: self.dummyRequest2, X_SET:{}}],
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
             R_LOG: [{REQUEST: self.dummyRequest1, X_SET:{}}],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(2)] + [{
                REP_STATE: {},
                R_LOG: [{REQUEST: self.dummyRequest2, X_SET:{}}],
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
             R_LOG: [{REQUEST: self.dummyRequest1, X_SET:{}}],
             PEND_REQS: [],
             REQ_Q: [],
             LAST_REQ: [],
             CON_FLAG: False,
            VIEW_CHANGE: False} for i in range(2)] + [{
                REP_STATE: {},
                R_LOG: [{REQUEST: self.dummyRequest1, X_SET:{}},
                        {REQUEST: self.dummyRequest2, X_SET:{}}],
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
            
        
    def test_stale_req_seqn(self):
        replication = ReplicationModule(0, self.resolver, 2, 1, 1)

        # The replica has executed a request with sequence number within the threshold
        replication.last_exec = MagicMock(return_value = 1)
        self.assertFalse(replication.stale_req_seqn())

        # The replica has executed a request with sequence number outside the threshold
        replication.last_exec = MagicMock(return_value = sys.maxsize - replication.SIGMA + 1)
        self.assertTrue(replication.stale_req_seqn())

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