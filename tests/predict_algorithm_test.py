import unittest
from unittest.mock import Mock, MagicMock
from resolve.resolver import Resolver
from modules.view_establishment.predicates import PredicatesAndAction
from modules.view_establishment.module import ViewEstablishmentModule
from resolve.enums import Function, Module
from modules.enums import ViewEstablishmentEnums


class TestPredicatesAndAction(unittest.TestCase):
    
    # Macros
    def test_stale_v(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)

        # Stale and in phase 0
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.legit_phs_zero = MagicMock(return_value = False)
        pred_module.legit_phs_one = MagicMock(return_value = False)
        self.assertTrue(pred_module.stale_v(0))
        # Stale and in phase 1
        view_est_mod.get_phs = MagicMock(return_value = 1)
        self.assertTrue(pred_module.stale_v(0))
        # Not stale
        pred_module.legit_phs_one = MagicMock(return_value = True)
        self.assertFalse(pred_module.stale_v(0))

    def test_legit_phs_zero(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        pred_module.type_check = MagicMock(return_value = True)
        vpair_to_test = {pred_module.CURRENT: 1, pred_module.NEXT: 1}

        # Legit to be in phase 0
        self.assertTrue(pred_module.legit_phs_zero(vpair_to_test))

        # Reset vpair, also legit
        vpair_to_test = {pred_module.CURRENT: pred_module.TEE, pred_module.NEXT: pred_module.DF_VIEW}
        self.assertTrue(pred_module.legit_phs_zero(vpair_to_test))

        # In view change, not legit to be in phase 0
        vpair_to_test = {pred_module.CURRENT: 1, pred_module.NEXT: 2}
        self.assertFalse(pred_module.legit_phs_zero(vpair_to_test))

        # Type check fails
        vpair_to_test = {pred_module.CURRENT: 1, pred_module.NEXT: 1}
        pred_module.type_check = MagicMock(return_value = False)
        self.assertFalse(pred_module.legit_phs_zero(vpair_to_test))

    def test_legit_phs_one(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        pred_module.type_check = MagicMock(return_value = True)
        vpair_to_test = {pred_module.CURRENT: 1, pred_module.NEXT: 2}

        # Legit to be in phase 1
        self.assertTrue(pred_module.legit_phs_one(vpair_to_test))

        # Not in a view change
        vpair_to_test = {pred_module.CURRENT: 1, pred_module.NEXT: 1}
        self.assertFalse(pred_module.legit_phs_one(vpair_to_test))

        # Type check fails
        vpair_to_test = {pred_module.CURRENT: 1, pred_module.NEXT: 2}
        pred_module.type_check = MagicMock(return_value = False)
        self.assertFalse(pred_module.legit_phs_one(vpair_to_test))


    def test_type_check(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)

        # Type check correct because current is valid, number of byzantine nodes = 2
        vpair_to_test = {pred_module.CURRENT: 0, pred_module.NEXT: 3}
        self.assertTrue(pred_module.type_check(vpair_to_test))

        # Type check correct because current is valid, number of byzantine nodes = 2
        vpair_to_test = {pred_module.CURRENT: pred_module.TEE, pred_module.NEXT: 3}
        self.assertTrue(pred_module.type_check(vpair_to_test))

        # Type check incorrect because next is not valid
        vpair_to_test = {pred_module.CURRENT: pred_module.TEE, pred_module.NEXT: pred_module.TEE}
        self.assertFalse(pred_module.type_check(vpair_to_test))
        
        # current is valid but next is not
        vpair_to_test = {pred_module.CURRENT: 0, pred_module.NEXT: pred_module.TEE}
        self.assertFalse(pred_module.type_check(vpair_to_test))

    def test_establish(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)

        # Should update to view 1 in current
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT: 1}]
        pred_module.establish()
        self.assertEqual(pred_module.views, [{pred_module.CURRENT: 1, pred_module.NEXT: 1}])

    def test_next_view(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)

        # Should update to view 1 in next
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT: 0}]
        pred_module.next_view()
        self.assertEqual(pred_module.views,[{pred_module.CURRENT: 0, pred_module.NEXT: 1}])

        # number of byzantine nodes = 2 so "next" should flip to view 0
        pred_module.views = [{pred_module.CURRENT: 1, pred_module.NEXT: 1}]
        pred_module.next_view()
        self.assertEqual(pred_module.views,[{pred_module.CURRENT: 1, pred_module.NEXT: 0}])


    def test_reset_v_change(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        pred_module.vChange = True
        pred_module.reset_v_change()
        self.assertFalse(pred_module.vChange)

    # Interface functions
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

        self.assertEqual(pred_module.reset_all(), ViewEstablishmentEnums.RESET)
        # The views has been reset to DEFAULT view pair
        self.assertEqual(pred_module.views, [{pred_module.CURRENT: None, pred_module.NEXT : 0}])
        # Assert that the init(reset) method at algorithm 1 and algorithm 3 are being called
        view_est_mod.init_module.assert_any_call()
        resolver.execute.assert_called_once_with(module=Module.REPLICATION_MODULE,
            func=Function.REP_REQUEST_RESET)

    def test_interface_get_view(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT : 0}, {pred_module.CURRENT: 1, pred_module.NEXT : 1}]
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
        self.assertIsNone(pred_module.get_view(0))

    def test_interface_allow_service(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        # Allow service settings
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT : 0}]
        pred_module.same_v_set = MagicMock(return_value = {0,0,0,0})
        self.assertTrue(pred_module.allow_service())

        #Deny service settings, creating a false statement for each condition
        view_est_mod.get_phs = MagicMock(return_value = 1)
        self.assertFalse(pred_module.allow_service())
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT : 1}]
        self.assertFalse(pred_module.allow_service())
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT : 0}]
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
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT : 0}, {pred_module.CURRENT: 1, pred_module.NEXT : 1}]
        # Should return node 1's view
        self.assertEqual(pred_module.get_info(1), {pred_module.CURRENT: 1, pred_module.NEXT : 1})

    def test_set_info(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT : 0}, {pred_module.CURRENT: 0, pred_module.NEXT : 0}]
        # Should change the view pair of node 1 
        pred_module.set_info({pred_module.CURRENT: 1, pred_module.NEXT : 1}, 1)
        self.assertEqual(pred_module.views[1], {pred_module.CURRENT: 1, pred_module.NEXT : 1})

    def test_automaton_phase_0_predicates(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        
        # Case 0
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT : 0}, {pred_module.CURRENT: 1, pred_module.NEXT : 1}]
        pred_module.transit_adopble = MagicMock(return_value = True)
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 0))
        # Not a adoptable view in transit
        pred_module.transit_adopble = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 0))
        # The adoptable view is the same as processor i
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT : 0}, {pred_module.CURRENT: 0, pred_module.NEXT : 0}]
        pred_module.transit_adopble = MagicMock(return_value = True)
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 0))

        # Case 1
        pred_module.establishable = MagicMock(return_value = True)
        pred_module.vChange = True
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 1))
        # View change is not required
        pred_module.vChange = False
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 1))
        # The threshold to move to a view change is not fulfilled
        pred_module.establishable = MagicMock(return_value = False)
        pred_module.vChange = True
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 1))

        # Case 2
        # There is a adoptable view in transit
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 2))
        # Non of the condition is fulfilled
        pred_module.transit_adopble = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 2))
        # Processor i view_pair is the default pair
        pred_module.views[pred_module.id] = pred_module.RST_PAIR
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 2))

        # Case 3 should return True
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 3))

    def test_automaton_phase_0_actions(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)

        # Case 0 should call adopt and next_view in view Establishment module
        view_est_mod.next_phs = Mock()
        pred_module.adopt = Mock()
        pred_module.reset_v_change = Mock()
        pred_module.view_pair_to_adopt = pred_module.RST_PAIR
        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 0, 0), ViewEstablishmentEnums.NO_RETURN_VALUE)
        view_est_mod.next_phs.assert_any_call()
        pred_module.reset_v_change.assert_any_call()
        pred_module.adopt.assert_called_once_with(pred_module.RST_PAIR)

        # Case 1 should call next_view and next_phs in view Establishment module
        pred_module.next_view = Mock()
        view_est_mod.next_phs = Mock()
        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 0, 1), ViewEstablishmentEnums.NO_RETURN_VALUE)
        pred_module.next_view.assert_any_call()
        view_est_mod.next_phs.assert_any_call()

        # Case 2 should return "No action" and call reset_v_change
        pred_module.reset_v_change = Mock()
        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 0, 2), ViewEstablishmentEnums.NO_ACTION)
        pred_module.reset_v_change.assert_any_call()

        # Case 3 should return "Reset"
        pred_module.reset_all = MagicMock(return_value = ViewEstablishmentEnums.RESET)
        pred_module.reset_v_change = Mock()
        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 0, 3), ViewEstablishmentEnums.RESET)
        pred_module.reset_v_change.assert_any_call()

        
    def test_automaton_phase_1_predicates(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)
        
        # Case 0
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT : 0}, {pred_module.CURRENT: 1, pred_module.NEXT : 1}]
        pred_module.transit_adopble = MagicMock(return_value = True)
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 1, 0))
        # Not a adoptable view in transit
        pred_module.transit_adopble = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 1, 0))
        # The adoptable view is the same as processor i
        pred_module.views = [{pred_module.CURRENT: 0, pred_module.NEXT : 0}, {pred_module.CURRENT: 0, pred_module.NEXT : 0}]
        pred_module.transit_adopble = MagicMock(return_value = True)
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 1, 0))

        # Case 1
        pred_module.establishable = MagicMock(return_value = True)
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 1, 1))
        # The threshold to move to a view change is not fulfilled
        pred_module.establishable = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 1, 1))

        # Case 2
        # There is not an adoptable view in transit
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 1, 2))
        # There is not an adoptable view in transit
        pred_module.transit_adopble = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 1, 2))

        # Case 3 should return True
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 1, 3))

    def test_automaton_phase_1_actions(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        pred_module = PredicatesAndAction(view_est_mod, resolver)

        # Case 0 should call adopt and next_view in view Establishment module
        pred_module.adopt = Mock()
        pred_module.reset_v_change = Mock()
        pred_module.view_pair_to_adopt = pred_module.RST_PAIR

        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 1, 0), ViewEstablishmentEnums.NO_RETURN_VALUE)
        pred_module.adopt.assert_called_once_with(pred_module.RST_PAIR)
        pred_module.reset_v_change.assert_any_call()

        # Case 1 should call next_view and next_phs in view Establishment module
        view_est_mod.next_phs = Mock()
        pred_module.reset_v_change = Mock()
        pred_module.establish = Mock()
        resolver.execute = Mock()
        pred_module.views[pred_module.id] = pred_module.RST_PAIR

        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 1, 1), ViewEstablishmentEnums.NO_RETURN_VALUE)
        view_est_mod.next_phs.assert_any_call()
        pred_module.reset_v_change.assert_any_call()
        pred_module.establish.assert_any_call()
        resolver.execute.assert_called_once_with(module=Module.REPLICATION_MODULE,
                        func=Function.REPLICA_FLUSH)

        # Case 2 should return "No action" and call reset_v_change
        pred_module.reset_v_change = Mock()
        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 1, 2), ViewEstablishmentEnums.NO_ACTION)
        pred_module.reset_v_change.assert_any_call()

        # Case 3 should return "Reset"
        pred_module.reset_all = MagicMock(return_value = ViewEstablishmentEnums.RESET)
        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 1, 3), ViewEstablishmentEnums.RESET)