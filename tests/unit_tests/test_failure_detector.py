import unittest
import os
from conf import config


from unittest.mock import Mock, MagicMock, call
from resolve.resolver import Resolver
from resolve.enums import Function, Module
from modules.replication.models.client_request import ClientRequest
from modules.replication.models.operation import Operation
from modules.enums import OperationEnums
from modules.primary_monitoring.failure_detector import FailureDetectorModule
from modules.constants import VIEW_CHANGE

class TestFailureDetector(unittest.TestCase):

    def setUp(self):
        self.resolver = Resolver(testing=True)
        self.clientRequest1 = ClientRequest(1, 1, Operation(OperationEnums.APPEND, 1))
        self.clientRequest2 = ClientRequest(2, 2, Operation(OperationEnums.APPEND, 2))

    def test_call_view_establishment_module(self):
        fail_det = FailureDetectorModule(0, self.resolver, 6, 1)
        fail_det.resolver.execute = MagicMock(return_value = 0)

        self.assertEqual(fail_det.get_current_view(0),0)
        fail_det.resolver.execute.assert_called_once_with(
            Module.VIEW_ESTABLISHMENT_MODULE,
            Function.GET_CURRENT_VIEW,
            0
        )

    def test_call_replication_module(self):
        fail_det = FailureDetectorModule(0, self.resolver, 6, 1)
        fail_det.resolver.execute = MagicMock(return_value = [2])

        self.assertEqual(fail_det.get_pend_reqs(),[2])
        fail_det.resolver.execute.assert_called_once_with(
            Module.REPLICATION_MODULE,
            Function.GET_PEND_REQS
        )
        fail_det.resolver.execute = MagicMock(return_value = VIEW_CHANGE)
        self.assertEqual(fail_det.get_pend_reqs(), [])

    def test_call_allow_serivce(self):
        fail_det = FailureDetectorModule(0, self.resolver, 6, 1)
        fail_det.resolver.execute = MagicMock(return_value = True)

        self.assertTrue(fail_det.allow_service())
        fail_det.resolver.execute.assert_called_once_with(
            Module.VIEW_ESTABLISHMENT_MODULE,
            Function.ALLOW_SERVICE
        )

    def test_reset(self):
        fail_det = FailureDetectorModule(0, self.resolver, 6, 1)
        # Change the values to non-default once
        fail_det.beat = [1 for i in range(6)]
        fail_det.cnt = 2
        fail_det.prim_susp = [True for i in range(6)]
        fail_det.cur_check_req = [ClientRequest(0, None, None)]

        fail_det.reset()
        self.assertEqual(fail_det.beat, [0 for i in range(6)])
        self.assertEqual(fail_det.cnt, 0)
        self.assertEqual(fail_det.prim_susp, [False for i in range(6)])
        self.assertEqual(fail_det.cur_check_req, [])


    def test_suspected(self):
        fail_det = FailureDetectorModule(0, self.resolver, 6, 1)
        # All has the same view and their primSusp is False
        fail_det.get_current_view = MagicMock(return_value = 0)
        self.assertFalse(fail_det.suspected())
        
        # Same view but primSusp is True for 3f+1 of them
        fail_det.prim_susp = [True, True, False, True, False, True]
        self.assertTrue(fail_det.suspected())

        # Now they are not in same view
        fail_det.prim_susp = [True for i in range(6)]
        fail_det.get_current_view = MagicMock(side_effect = lambda x: x%2)
        # just double checking the re-assignment of prim_susp
        self.assertTrue(fail_det.prim_susp[2])
        self.assertFalse(fail_det.suspected())

    def test_check_progress_by_prim(self):
        fail_det = FailureDetectorModule(0, self.resolver, 6, 1)
        fail_det.resolver.execute = MagicMock(return_value = [self.clientRequest1])
        fail_det.cur_check_req = [self.clientRequest1, self.clientRequest2]

        # let cnt not be default value
        fail_det.cnt = 2
        # There has been progress since clientRequest2 is missing in get_pend_reqs
        fail_det.check_progress_by_prim(1)
        self.assertEqual(fail_det.cur_check_req, [self.clientRequest1])
        self.assertEqual(fail_det.cnt, 0)

        # There has been no progress, cnt should be incremented
        fail_det.cur_check_req = [self.clientRequest1]        
        fail_det.check_progress_by_prim(1)
        self.assertEqual(fail_det.cnt, 1)

        # cur_check_req is empty, cnt should be reset
        fail_det.cur_check_req = []        
        fail_det.check_progress_by_prim(1)
        self.assertEqual(fail_det.cnt, 0)

    def test_update_beat(self):
        fail_det = FailureDetectorModule(0, self.resolver, 6, 1)
        fail_det.beat = [i for i in range(6)]
        fail_det.update_beat(3)
        
        # All except Node 0 and 3 should increment with 1,
        # Node 0 and 3 should be set to 0
        self.assertEqual(fail_det.beat, [0, 2, 3, 0, 5, 6])
        self.assertEqual(fail_det.fd_set, {0,1,2,3,4,5})

        fail_det.beat = [i for i in range(5)] + [99]
        fail_det.update_beat(3)
        
        # All except Node 0 and 3 should increment with 1,
        # Node 0 and 3 should be set to 0
        # Node 5 is above the threshold and should not be in fd_set
        self.assertEqual(fail_det.beat, [0, 2, 3, 0, 5, 100])
        self.assertEqual(fail_det.fd_set, {0,1,2,3,4})

    def test_upon_token_from_pj(self):
        fail_det = FailureDetectorModule(0, self.resolver, 6, 1)
        
        self.resolver.execute = MagicMock(return_value = True)
        fail_det.allow_service = MagicMock(return_value = True)
        fail_det.check_progress_by_prim = Mock()
        fail_det.get_current_view = MagicMock(return_value = 1)
        fail_det.beat = [i for i in range(6)]
        fail_det.prim = 1

        fail_det.cnt = 1
        fail_det.upon_token_from_pj(1, False)
        # Update beat should be called
        self.assertEqual(fail_det.beat, [0, 0, 3, 4, 5, 6])
        self.assertEqual(fail_det.fd_set, {0,1,2,3,4,5})

        # 1 is the new primary hence check_progress_by_prim should be called
        fail_det.check_progress_by_prim.assert_called_once_with(1)
        # prim != self.id, hence cnt should not be reset, since we mock check_progress
        self.assertNotEqual(fail_det.cnt, 0)
        # 0 is in fd_set and cnt < Threshold
        self.assertFalse(fail_det.prim_susp[0])

        # Cnt is above threshold
        fail_det.cnt = 101
        fail_det.upon_token_from_pj(1, False)
        self.assertTrue(fail_det.prim_susp[0])

        # Reset the prim_susp and test other condition
        fail_det.prim_susp[0] = False
        fail_det.beat[1] = 101
        fail_det.cnt = 0
        self.assertFalse(fail_det.prim_susp[0])
        fail_det.upon_token_from_pj(1)
        self.assertTrue(fail_det.prim_susp[0])

    def test_upon_token_from_pj(self):

        fail_det = FailureDetectorModule(0, self.resolver, 6, 1)
        
        self.resolver.execute = MagicMock(return_value = True)
        fail_det.allow_service = MagicMock(return_value = True)
        fail_det.check_progress_by_prim = Mock()
        fail_det.get_current_view = MagicMock(return_value = 0)
        fail_det.beat = [i for i in range(6)]
        fail_det.prim = 0

        fail_det.cnt = 1
        fail_det.upon_token_from_pj(1, False)
        # Update beat should be called
        self.assertEqual(fail_det.beat, [0, 0, 3, 4, 5, 6])
        self.assertEqual(fail_det.fd_set, {0,1,2,3,4,5})

        # self.id is the new primary hence check_progress_by_prim should not be called
        fail_det.check_progress_by_prim.assert_not_called()
        # prim == self.id, hence cnt should be reset
        self.assertEqual(fail_det.cnt, 0)
        # 0 is in fd_set and cnt < Threshold
        self.assertFalse(fail_det.prim_susp[0])
        
        fail_det.reset = Mock()
        fail_det.allow_service = MagicMock(return_value = False)
        fail_det.upon_token_from_pj(2, False)
        fail_det.reset.assert_called_once()
        

