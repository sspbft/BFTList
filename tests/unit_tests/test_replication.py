import unittest
from unittest.mock import Mock, MagicMock
from resolve.resolver import Resolver
from modules.replication.module import ReplicationModule
from resolve.enums import Function, Module
from modules.enums import ReplicationEnums


class TestReplicationModule(unittest.TestCase):

    def setUp(self):
        self.resolver = Resolver()

    
    def test_resolver_can_be_initialized(self):
        replication = ReplicationModule(0, self.resolver, 2, 0)
        self.assertIsNotNone(replication)

    # Macros

    def test_flush_local(self):
        replication = ReplicationModule(0, self.resolver, 2, 0)
        replication.flush_local()
        # The local variables should be the default values
        rep_default = [{replication.REP_STATE: {},
             replication.R_LOG: [],
             replication.PEND_REQS: [],
             replication.REQ_Q: [],
             replication.LAST_REQ: [],
             replication.CON_FLAG: False,
             replication.VIEW_CHANGE: False},
             {replication.REP_STATE: {},
             replication.R_LOG: [],
             replication.PEND_REQS: [],
             replication.REQ_Q: [],
             replication.LAST_REQ: [],
             replication.CON_FLAG: False,
             replication.VIEW_CHANGE: False}]
        self.assertEqual(replication.seq_n, 0)
        self.assertEqual(replication.rep, rep_default)

    def test_msg(self):
        replication = ReplicationModule(0, self.resolver, 2, 0)
        valid_request = {replication.REQUEST: 1, replication.STATUS: ReplicationEnums.PRE_PREP}
        replication.rep[1] = {
             replication.REP_STATE: {},
             replication.R_LOG: [],
             replication.PEND_REQS: [],
             replication.REQ_Q: [
                 {replication.REQUEST: 1, replication.STATUS: ReplicationEnums.PRE_PREP},
                 {replication.REQUEST: 2, replication.STATUS: ReplicationEnums.PREP},],
             replication.LAST_REQ: [],
             replication.CON_FLAG: False,
             replication.VIEW_CHANGE: False}

        self.assertEqual(replication.msg(ReplicationEnums.PRE_PREP, 1), {1})

    # Interface functions

    def test_get_pend_reqs(self):
        replication = ReplicationModule(0, self.resolver, 2, 0)

        # Should return the intersection of the two sets, meaning {2}
        replication.unassigned_reqs = MagicMock(return_value = {1,2})
        replication.known_pend_reqs = MagicMock(return_value = {2,3})
        replication.view_changed = False
        self.assertEqual(replication.get_pend_reqs(), {2})

    def test_rep_request_reset(self):
        replication = ReplicationModule(0, self.resolver, 2, 0)

        # Should return false
        replication.need_flush = False
        self.assertFalse(replication.rep_request_reset())

        # Should change need_flush and return true
        replication.need_flush = True
        self.assertTrue(replication.rep_request_reset())
        self.assertFalse(replication.need_flush)

    def test_replica_flush(self):
        replication = ReplicationModule(0, self.resolver, 2, 0)

        # Should change flush to True
        replication.flush = False
        replication.replica_flush()
        self.assertTrue(replication.flush)