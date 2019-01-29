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
        view_est_mod.get_phs = MagicMock(return_value = 1)
        view_est_mod.witnes_seen = MagicMock(return_value = True)
        pred_module.allow_service = MagicMock(return_value = True)

        # Should return the view of the current node
        self.assertEqual(pred_module.get_view(0), 0)
        # Should return the view of an other processor
        self.assertEqual(pred_module.get_view(1), 1)
        # Should give back the TEE (None) by denying service
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.allow_service = MagicMock(return_value = False)
        self.assertIsNone(pred_module.get_view(1))

    def test_interface_allow_service(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        # Allow service settings
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.views = [{"current": 0, "next" : 0}]
        pred_module.same_v_set = MagicMock(return_value = {0,0,0,0})
        self.assertTrue(pred_module.allow_service())

        #Deny service settings, creating a false statement for each condition
        view_est_mod.get_phs = MagicMock(return_value = 1)
        self.assertFalse(pred_module.allow_service())
        view_est_mod.get_phs = MagicMock(return_value = 0)
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

    def test_automaton_phase_0_predicates(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        
        # Case 0
        pred_module.views = [{"current": 0, "next" : 0}, {"current": 1, "next" : 1}]
        pred_module.transit_adopble = MagicMock(return_value = True)
        self.assertTrue(pred_module.automation("pred", 0, 0))
        # Not a adoptable view in transit
        pred_module.transit_adopble = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation("pred", 0, 0))
        # The adoptable view is the same as processor i
        pred_module.views = [{"current": 0, "next" : 0}, {"current": 0, "next" : 0}]
        pred_module.transit_adopble = MagicMock(return_value = True)
        self.assertFalse(pred_module.automation("pred", 0, 0))

        # Case 1
        pred_module.establishable = MagicMock(return_value = True)
        pred_module.vChange = True
        self.assertTrue(pred_module.automation("pred", 0, 1))
        # View change is not required
        pred_module.vChange = False
        self.assertFalse(pred_module.automation("pred", 0, 1))
        # The threshold to move to a view change is not fulfilled
        pred_module.establishable = MagicMock(return_value = False)
        pred_module.vChange = True
        self.assertFalse(pred_module.automation("pred", 0, 1))

        # Case 2
        # There is a adoptable view in transit
        self.assertTrue(pred_module.automation("pred", 0, 2))
        # Non of the condition is fulfilled
        pred_module.transit_adopble = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation("pred", 0, 2))
        # Processor i view_pair is the default pair
        pred_module.views[pred_module.id] = pred_module.RST_PAIR
        self.assertTrue(pred_module.automation("pred", 0, 2))

        # Case 3 should return True
        self.assertTrue(pred_module.automation("pred", 0, 3))

    def test_automaton_phase_0_actions(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)

        # Case 0 should call adopt and next_view in view Establishment module
        view_est_mod.next_phs = Mock()
        pred_module.adopt = Mock()
        pred_module.reset_v_change = Mock()
        pred_module.view_pair_to_adopt = pred_module.RST_PAIR
        self.assertEqual(pred_module.automation("act", 0, 0), "Adopted new view")
        view_est_mod.next_phs.assert_any_call()
        pred_module.reset_v_change.assert_any_call()
        pred_module.adopt.assert_called_once_with(pred_module.RST_PAIR)

        # Case 1 should call next_view and next_phs in view Establishment module
        pred_module.next_view = Mock()
        view_est_mod.next_phs = Mock()
        self.assertEqual(pred_module.automation("act", 0, 1), "Incremented view")
        pred_module.next_view.assert_any_call()
        view_est_mod.next_phs.assert_any_call()

        # Case 2 should return "No action" and call reset_v_change
        pred_module.reset_v_change = Mock()
        self.assertEqual(pred_module.automation("act", 0, 2), "No action")
        pred_module.reset_v_change.assert_any_call()

        # Case 3 should return "Reset"
        pred_module.reset_all = MagicMock(return_value = "Reset")
        self.assertEqual(pred_module.automation("act", 0, 3), "Reset")
        
        
    def test_automaton_phase_1_predicates(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        
        # Case 0
        pred_module.views = [{"current": 0, "next" : 0}, {"current": 1, "next" : 1}]
        pred_module.transit_adopble = MagicMock(return_value = True)
        self.assertTrue(pred_module.automation("pred", 1, 0))
        # Not a adoptable view in transit
        pred_module.transit_adopble = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation("pred", 1, 0))
        # The adoptable view is the same as processor i
        pred_module.views = [{"current": 0, "next" : 0}, {"current": 0, "next" : 0}]
        pred_module.transit_adopble = MagicMock(return_value = True)
        self.assertFalse(pred_module.automation("pred", 1, 0))

        # Case 1
        pred_module.establishable = MagicMock(return_value = True)
        self.assertTrue(pred_module.automation("pred", 1, 1))
        # The threshold to move to a view change is not fulfilled
        pred_module.establishable = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation("pred", 1, 1))

        # Case 2
        # There is not an adoptable view in transit
        self.assertTrue(pred_module.automation("pred", 1, 2))
        # There is not an adoptable view in transit
        pred_module.transit_adopble = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation("pred", 1, 2))

        # Case 3 should return True
        self.assertTrue(pred_module.automation("pred", 1, 3))

    def test_automaton_phase_1_actions(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)

        # Case 0 should call adopt and next_view in view Establishment module
        pred_module.adopt = Mock()
        pred_module.reset_v_change = Mock()
        pred_module.view_pair_to_adopt = pred_module.RST_PAIR

        self.assertEqual(pred_module.automation("act", 1, 0), "Adopted new view")
        pred_module.adopt.assert_called_once_with(pred_module.RST_PAIR)
        pred_module.reset_v_change.assert_any_call()

        # Case 1 should call next_view and next_phs in view Establishment module
        view_est_mod.next_phs = Mock()
        pred_module.reset_v_change = Mock()
        pred_module.establish = Mock()
        resolver.execute = Mock()
        pred_module.views[pred_module.id] = pred_module.RST_PAIR

        self.assertEqual(pred_module.automation("act", 1, 1), "Established new view")
        view_est_mod.next_phs.assert_any_call()
        pred_module.reset_v_change.assert_any_call()
        pred_module.establish.assert_any_call()
        resolver.execute.assert_called_once_with(module=Module.REPLICATION_MODULE,
                        func=Function.REPLICA_FLUSH)

        # Case 2 should return "No action" and call reset_v_change
        pred_module.reset_v_change = Mock()
        self.assertEqual(pred_module.automation("act", 1, 2), "No action")
        pred_module.reset_v_change.assert_any_call()

        # Case 3 should return "Reset"
        pred_module.reset_all = MagicMock(return_value = "Reset")
        self.assertEqual(pred_module.automation("act", 1, 3), "Reset")