import unittest
from unittest.mock import Mock, MagicMock
from resolve.resolver import Resolver
from modules.view_establishment.predicates import PredicatesAndAction
from modules.view_establishment.module import ViewEstablishmentModule
from resolve.enums import Function, Module


# TODO implement more tests
class TestPredicatesAndAction(unittest.TestCase):
    
    def test_predicate_can_be_initialized(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        self.assertIsNotNone(pred_module)

    def test_need_reset(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        
        pred_module.stale_v = MagicMock(return_value = True)
        resolver.execute = MagicMock(return_value = True)
        self.assertTrue(pred_module.need_reset())

        resolver.execute = MagicMock(return_value = False)
        self.assertFalse(pred_module.need_reset())

        pred_module.stale_v = MagicMock(return_value = False)
        resolver.execute = MagicMock(return_value = True)
        self.assertFalse(pred_module.need_reset())

    def test_reset_all(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver, 1)
        view_est_mod.init_module = MagicMock()
        resolver.execute = MagicMock()

        self.assertEqual(pred_module.reset_all(), "Reset")
        # The views has been reset to DEFAULT view pair
        self.assertEqual(pred_module.views, [{"current": None, "next" : 0}])
        # Assert that the init(reset) method at algorithm 1 and algorithm 3 are being called
        view_est_mod.init_module.assert_any_call()
        resolver.execute.assert_called_once_with(module=Module.REPLICATION_MODULE,
            func=Function.REP_REQUEST_RESET)

    def test_interface_get_view(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        pred_module.views = [{"current": 0, "next" : 0}, {"current": 1, "next" : 1}]
        view_est_mod.phs = [1]
        view_est_mod.witnes_seen = MagicMock(return_value = True)
        pred_module.allow_service = MagicMock(return_value = True)

        # Should return the view of the current node
        self.assertEqual(pred_module.get_view(0), 0)
        # Should return the view of an other processor
        self.assertEqual(pred_module.get_view(1), 1)
        # Should give back the TEE (None) by denying service
        view_est_mod.phs = [0]
        pred_module.allow_service = MagicMock(return_value = False)
        self.assertIsNone(pred_module.get_view(1))

    def test_interface_allow_service(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        # Allow service settings
        view_est_mod.phs = [0]
        pred_module.views = [{"current": 0, "next" : 0}]
        pred_module.same_v_set = MagicMock(return_value = {0,0,0,0})
        self.assertTrue(pred_module.allow_service())

        #Deny service settings, creating a false statement for each condition
        view_est_mod.phs = [1]
        self.assertFalse(pred_module.allow_service())
        view_est_mod.phs = [0]
        pred_module.views = [{"current": 0, "next" : 1}]
        self.assertFalse(pred_module.allow_service())
        pred_module.views = [{"current": 0, "next" : 0}]
        pred_module.same_v_set = MagicMock(return_value = {})
        self.assertFalse(pred_module.allow_service())

    def test_interface_view_change(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        # Should change vChange to true
        pred_module.view_change()
        self.assertTrue(pred_module.vChange)

    def test_auto_max_case(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        # Should return the max case for each of the phases
        self.assertEqual(pred_module.auto_max_case(0), 3)
        self.assertEqual(pred_module.auto_max_case(1), 3)

    def test_get_info(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        pred_module.views = [{"current": 0, "next" : 0}, {"current": 1, "next" : 1}]
        # Should return node 1's view
        self.assertEqual(pred_module.get_info(1), {"current": 1, "next" : 1})

    def test_set_info(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        pred_module.views = [{"current": 0, "next" : 0}, {"current": 0, "next" : 0}]
        # Should change the view pair of node 1 
        pred_module.set_info({"current": 1, "next" : 1}, 1)
        self.assertEqual(pred_module.views[1], {"current": 1, "next" : 1})

