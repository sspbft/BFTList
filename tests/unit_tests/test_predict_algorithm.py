import unittest
from unittest.mock import Mock, MagicMock
from resolve.resolver import Resolver
from modules.view_establishment.predicates import PredicatesAndAction
from modules.view_establishment.module import ViewEstablishmentModule
from resolve.enums import Function, Module
from modules.enums import ViewEstablishmentEnums
from modules.constants import CURRENT, NEXT


class TestPredicatesAndAction(unittest.TestCase):

    def setUp(self):
        self.resolver = Resolver(testing=True)

    def test_valid(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 5, 0)
        v_pair = {CURRENT: ViewEstablishmentEnums.TEE, NEXT: ViewEstablishmentEnums.DF_VIEW}
        msg_to_valid = [0, False, v_pair]
        self.assertTrue(view_est_mod.pred_and_action.valid(msg_to_valid))
        msg_to_valid = [1, False, {CURRENT: 1, NEXT: 1}]
        self.assertFalse(view_est_mod.pred_and_action.valid(msg_to_valid))

    # Macros
    def test_stale_v(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)

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
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        pred_module.type_check = MagicMock(return_value = True)
        vpair_to_test = {CURRENT: 1, NEXT: 1}

        # Legit to be in phase 0
        self.assertTrue(pred_module.legit_phs_zero(vpair_to_test))

        # Reset vpair, also legit
        vpair_to_test = pred_module.RST_PAIR
        self.assertTrue(pred_module.legit_phs_zero(vpair_to_test))

        # In view change, not legit to be in phase 0
        vpair_to_test = {CURRENT: 1, NEXT: 2}
        self.assertFalse(pred_module.legit_phs_zero(vpair_to_test))

        # Type check fails
        vpair_to_test = {CURRENT: 1, NEXT: 1}
        pred_module.type_check = MagicMock(return_value = False)
        self.assertFalse(pred_module.legit_phs_zero(vpair_to_test))

    def test_legit_phs_one(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        pred_module.type_check = MagicMock(return_value = True)
        vpair_to_test = {CURRENT: 1, NEXT: 2}

        # Legit to be in phase 1
        self.assertTrue(pred_module.legit_phs_one(vpair_to_test))

        # Not in a view change
        vpair_to_test = {CURRENT: 1, NEXT: 1}
        self.assertFalse(pred_module.legit_phs_one(vpair_to_test))

        # Type check fails
        vpair_to_test = {CURRENT: 1, NEXT: 2}
        pred_module.type_check = MagicMock(return_value = False)
        self.assertFalse(pred_module.legit_phs_one(vpair_to_test))

    def test_type_check(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 5, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 5, 0)

        # Type check correct because current is valid, number of nodes = 5
        vpair_to_test = {CURRENT: 0, NEXT: 3}
        self.assertTrue(pred_module.type_check(vpair_to_test))

        # Type check correct because current is valid, number of 5
        vpair_to_test = {CURRENT: ViewEstablishmentEnums.TEE, NEXT: 3}
        self.assertTrue(pred_module.type_check(vpair_to_test))

        # Type check incorrect because next is not valid
        vpair_to_test = {CURRENT: ViewEstablishmentEnums.TEE, NEXT: ViewEstablishmentEnums.TEE}
        self.assertFalse(pred_module.type_check(vpair_to_test))
        
        # current is valid but next is not
        vpair_to_test = {CURRENT: 0, NEXT: ViewEstablishmentEnums.TEE}
        self.assertFalse(pred_module.type_check(vpair_to_test))

    def test_valid(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        # A msg has the following structure:[phase, witnesses, view_pair]

        # The view pairs are allowed in the corresponding phase
        msg_to_valid = [0, {}, {"current": 0, "next": 0}]
        self.assertTrue(view_est_mod.pred_and_action.valid(msg_to_valid))
        msg_to_valid = [1, {}, {"current": 0, "next": 1}]
        self.assertTrue(view_est_mod.pred_and_action.valid(msg_to_valid))
        # The view pairs are not allowed in the corresponding phase
        msg_to_valid = [0, {}, {"current": 0, "next": 1}]
        self.assertFalse(view_est_mod.pred_and_action.valid(msg_to_valid))
        msg_to_valid = [1, {}, {"current": 0, "next": 0}]
        self.assertFalse(view_est_mod.pred_and_action.valid(msg_to_valid))


    def test_same_v_set(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)

        # Both processors are in the same view and phase
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.stale_v = MagicMock(return_value = False)
        pred_module.views = [{CURRENT: 0, NEXT: 0}, {CURRENT: 0, NEXT: 0}]
        self.assertEqual(pred_module.same_v_set(0, 0), {0, 1})

        # Processor 1 is not in the same view and but same phase
        pred_module.views = [{CURRENT: 0, NEXT: 0}, {CURRENT: 0, NEXT: 1}]
        self.assertEqual(pred_module.same_v_set(0, 0), {0})
        
        # Processor 1 is in the same view and but not in same phase
        view_est_mod.get_phs = MagicMock(side_effect=lambda x: x) # Returns the input value (works for this specific case)
        pred_module.views = [{CURRENT: 0, NEXT: 0}, {CURRENT: 0, NEXT: 0}]
        self.assertEqual(pred_module.same_v_set(0, 0), {0})

        # Processors are stale, should return empty set
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.stale_v = MagicMock(return_value = True)
        pred_module.views = [{CURRENT: 0, NEXT: 0}, {CURRENT: 0, NEXT: 0}]
        self.assertEqual(pred_module.same_v_set(0, 0), set())

    def test_transit_set(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)

        # All is well
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.stale_v = MagicMock(return_value = False)
        pred_module.transition_cases = MagicMock(return_value = True)
        self.assertEqual(pred_module.transit_set(0, 1, ViewEstablishmentEnums.FOLLOW), {0,1})

        # Different phases, node 0 in phase 1 and node 1 in phase 0
        view_est_mod.get_phs = MagicMock(side_effect=lambda x: (x+1) % 2)
        self.assertEqual(pred_module.transit_set(0, 1, ViewEstablishmentEnums.FOLLOW), {1})

        # Transition case returns false
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.transition_cases = MagicMock(return_value = False)
        self.assertEqual(pred_module.transit_set(0, 1, ViewEstablishmentEnums.FOLLOW), set())

        # Both processors are stale
        pred_module.stale_v = MagicMock(return_value = True)
        pred_module.transition_cases = MagicMock(return_value = True)
        self.assertEqual(pred_module.transit_set(0, 1, ViewEstablishmentEnums.FOLLOW), set())

    def test_transit_adopble(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)

        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.number_of_byzantine = 1
        # Mocks sets which union does not add up to 4, should return false
        pred_module.transit_set = MagicMock(return_value = {1})
        pred_module.same_v_set = MagicMock(return_value = {1,2,3})
        self.assertFalse(pred_module.transit_adopble(0, 0, ViewEstablishmentEnums.FOLLOW))

        # Mocks sets which union adds up to 4, should return true
        pred_module.same_v_set = MagicMock(return_value = {2,3,4})
        self.assertTrue(pred_module.transit_adopble(0, 0, ViewEstablishmentEnums.REMAIN))

    def test_transition_cases(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        view_pair_to_test = {CURRENT: 0, NEXT: 1}
        
        # Mode REMAIN both phases, one 
        pred_module.views[pred_module.id].update({CURRENT: 1, NEXT: 1})
        self.assertTrue(pred_module.transition_cases(0, view_pair_to_test, 0, ViewEstablishmentEnums.REMAIN))
        pred_module.views[pred_module.id].update({CURRENT: 0, NEXT: 0})
        self.assertFalse(pred_module.transition_cases(0, view_pair_to_test, 1, ViewEstablishmentEnums.REMAIN))

        # Mode FOLLOW, phase 0 should return true
        self.assertTrue(pred_module.transition_cases(0, view_pair_to_test, 0, ViewEstablishmentEnums.FOLLOW))
        # Mode FOLLOW, phase 0 should return false
        pred_module.views[pred_module.id].update({CURRENT: 1, NEXT: 1})
        self.assertFalse(pred_module.transition_cases(0, view_pair_to_test, 0, ViewEstablishmentEnums.FOLLOW))

        # Mode FOLLOW, phase 1 should return false
        self.assertFalse(pred_module.transition_cases(0, view_pair_to_test, 1, ViewEstablishmentEnums.FOLLOW))
        
        # Mode FOLLOW, phase 1 should return true
        pred_module.views[pred_module.id].update({CURRENT: 0, NEXT: 0})
        self.assertTrue(pred_module.transition_cases(0, view_pair_to_test, 1, ViewEstablishmentEnums.FOLLOW))


    def test_adopt(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)

        # Default pred_module.views = {self.CURRENT: TEE, self.NEXT: DF_VIEW}
        vpair_to_test = {CURRENT: 1, NEXT: 1}
        view_est_mod.pred_and_action.adopt(vpair_to_test)
        self.assertEqual(view_est_mod.pred_and_action.views[view_est_mod.pred_and_action.id],
                        {CURRENT: ViewEstablishmentEnums.TEE, NEXT: 1})

    def test_establishable(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)

        # Mocks sets that does not add up to , should return false
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.transit_set = MagicMock(return_value = set())
        pred_module.same_v_set = MagicMock(return_value = set())
        self.assertFalse(pred_module.establishable(0, ViewEstablishmentEnums.FOLLOW))
        
        # Mocks sets that adds up to over 1 , should return true
        pred_module.transit_set = MagicMock(return_value = {1})
        pred_module.same_v_set= MagicMock(return_value = {1})
        self.assertTrue(pred_module.establishable(0, ViewEstablishmentEnums.REMAIN))
        

    def test_establish(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)

        # Should update to view 1 in current
        pred_module.views = [{CURRENT: 0, NEXT: 1}]
        pred_module.establish()
        self.assertEqual(pred_module.views, [{CURRENT: 1, NEXT: 1}])

    def test_next_view(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)

        # Should update to view 1 in next
        pred_module.views = [{CURRENT: 0, NEXT: 0}]
        pred_module.next_view()
        self.assertEqual(pred_module.views,[{CURRENT: 0, NEXT: 1}])

        # number of byzantine nodes = 2 so "next" should flip to view 0
        pred_module.views = [{CURRENT: 1, NEXT: 1}]
        pred_module.next_view()
        self.assertEqual(pred_module.views,[{CURRENT: 1, NEXT: 0}])


    def test_reset_v_change(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        pred_module.vChange = True
        pred_module.reset_v_change()
        self.assertFalse(pred_module.vChange)

    # Interface functions
    def test_predicate_can_be_initialized(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        self.assertIsNotNone(pred_module)

    def test_need_reset(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        
        pred_module.stale_v = MagicMock(return_value = True)
        self.resolver.execute = MagicMock(return_value = True)
        self.assertTrue(pred_module.need_reset())

        pred_module.stale_v = MagicMock(return_value = False)
        self.assertTrue(pred_module.need_reset())

        self.resolver.execute = MagicMock(return_value = False)
        self.assertFalse(pred_module.need_reset())

    def test_reset_all(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 1, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 1, 0)
        view_est_mod.init_module = MagicMock()
        self.resolver.execute = MagicMock()

        self.assertEqual(pred_module.reset_all(), ViewEstablishmentEnums.RESET)
        # The views has been reset to DEFAULT view pair
        self.assertEqual(pred_module.views, [pred_module.RST_PAIR])
        # Assert that the init(reset) method at algorithm 1 and algorithm 3 are being called
        view_est_mod.init_module.assert_any_call()
        self.resolver.execute.assert_called_once_with(module=Module.REPLICATION_MODULE,
            func=Function.REP_REQUEST_RESET)

    def test_interface_get_current_view(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        pred_module.views = [{CURRENT: 0, NEXT : 0}, {CURRENT: 1, NEXT : 1}]
        view_est_mod.get_phs = MagicMock(return_value = 1)
        view_est_mod.witnes_seen = MagicMock(return_value = True)
        pred_module.allow_service = MagicMock(return_value = True)

        # Should return the view of the current node
        self.assertEqual(pred_module.get_current_view(0), 0)
        # Should return the view of an other processor
        self.assertEqual(pred_module.get_current_view(1), 1)
        # Should give back the TEE (None) by denying service
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.allow_service = MagicMock(return_value = False)
        self.assertEqual(pred_module.get_current_view(0), ViewEstablishmentEnums.TEE)

    def test_interface_allow_service(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        # Allow service settings
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.views = [{CURRENT: 0, NEXT : 0}]
        pred_module.same_v_set = MagicMock(return_value = {0,0,0,0})
        self.assertTrue(pred_module.allow_service())

        #Deny service settings, creating a false statement for each condition
        view_est_mod.get_phs = MagicMock(return_value = 1)
        self.assertFalse(pred_module.allow_service())
        view_est_mod.get_phs = MagicMock(return_value = 0)
        pred_module.views = [{CURRENT: 0, NEXT : 1}]
        self.assertFalse(pred_module.allow_service())
        pred_module.views = [{CURRENT: 0, NEXT : 0}]
        pred_module.same_v_set = MagicMock(return_value = {})
        self.assertFalse(pred_module.allow_service())

    def test_interface_view_change(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        # Should change vChange to true
        pred_module.view_change()
        self.assertTrue(pred_module.vChange)

    def test_auto_max_case(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        # Should return the max case for each of the phases
        self.assertEqual(pred_module.auto_max_case(0), 3)
        self.assertEqual(pred_module.auto_max_case(1), 3)

    def test_get_info(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        pred_module.views = [{CURRENT: 0, NEXT : 0}, {CURRENT: 1, NEXT : 1}]
        # Should return node 1's view
        self.assertEqual(pred_module.get_info(1), {CURRENT: 1, NEXT : 1})

    def test_set_info(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        pred_module.views = [{CURRENT: 0, NEXT : 0}, {CURRENT: 0, NEXT : 0}]
        # Should change the view pair of node 1 
        pred_module.set_info({CURRENT: 1, NEXT : 1}, 1)
        self.assertEqual(pred_module.views[1], {CURRENT: 1, NEXT : 1})

    def test_added_logic_phase_0_case_1_b(self):
        # No mocking needed, establishable should return true
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        pred_module.vChange = False
        pred_module.views = [pred_module.RST_PAIR, pred_module.RST_PAIR]
        view_est_mod.phs = [0, 0]
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 1))

    def test_automaton_phase_0_predicates(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        
        # Case 0
        pred_module.views = [{CURRENT: 0, NEXT : 0}, {CURRENT: 1, NEXT : 1}]
        pred_module.transit_adopble = MagicMock(return_value = True)
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 0))
        # Not a adoptable view in transit
        pred_module.transit_adopble = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 0))
        # The adoptable view is the same as processor i
        pred_module.views = [{CURRENT: 0, NEXT : 0}, {CURRENT: 0, NEXT : 0}]
        pred_module.transit_adopble = MagicMock(return_value = True)
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 0))
        
        # Case 1b
        pred_module.vChange = False
        pred_module.establishable = MagicMock(return_value = True)
        pred_module.views[pred_module.id] = pred_module.RST_PAIR
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 1))

        # Case 1a
        pred_module.views[pred_module.id] = {"current": 1, "next": 1}  # NOT the RST_PAIR
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
        # None of the condition is fulfilled
        pred_module.transit_adopble = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 2))
        # Processor i view_pair is the default pair
        pred_module.views[pred_module.id] = pred_module.RST_PAIR
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 2))

        # Case 3 should return True
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 0, 3))

    def test_automaton_phase_0_actions(self):
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)

        # Case 0 should call adopt and next_view in view Establishment module
        view_est_mod.next_phs = Mock()
        pred_module.adopt = Mock()
        pred_module.reset_v_change = Mock()
        pred_module.view_pair_to_adopt = pred_module.RST_PAIR
        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 0, 0), ViewEstablishmentEnums.NO_RETURN_VALUE)
        view_est_mod.next_phs.assert_any_call()
        pred_module.reset_v_change.assert_any_call()
        pred_module.adopt.assert_called_once_with(pred_module.RST_PAIR)

        # Case 1a should call next_view and next_phs in view Establishment module
        pred_module.next_view = Mock()
        view_est_mod.next_phs = Mock()
        pred_module.vChange = True
        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 0, 1), ViewEstablishmentEnums.NO_RETURN_VALUE)
        pred_module.next_view.assert_any_call()
        view_est_mod.next_phs.assert_any_call()

        # Case 1b should call next_phs in View Establishment module
        pred_module.vChange = False
        view_est_mod.next_phs = Mock()
        pred_module.views[pred_module.id] = pred_module.RST_PAIR
        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 0, 1), ViewEstablishmentEnums.NO_RETURN_VALUE)
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
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)
        
        # Case 0
        pred_module.views = [{CURRENT: 0, NEXT : 4}, {CURRENT: 1, NEXT : 1}]
        pred_module.transit_adopble = MagicMock(return_value = True)
        self.assertTrue(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 1, 0))
        
        # Not a adoptable view in transit
        pred_module.transit_adopble = MagicMock(return_value = False)
        self.assertFalse(pred_module.automation(ViewEstablishmentEnums.PREDICATE, 1, 0))
        # The adoptable view is the same as processor i
        pred_module.views = [{CURRENT: 0, NEXT : 0}, {CURRENT: 0, NEXT : 0}]
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
        view_est_mod = ViewEstablishmentModule(0, self.resolver, 2, 0)
        pred_module = PredicatesAndAction(view_est_mod, 0, self.resolver, 2, 0)

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
        self.resolver.execute = Mock()
        pred_module.views[pred_module.id] = pred_module.RST_PAIR

        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 1, 1), ViewEstablishmentEnums.NO_RETURN_VALUE)
        view_est_mod.next_phs.assert_any_call()
        pred_module.reset_v_change.assert_any_call()
        pred_module.establish.assert_any_call()
        # self.resolver.execute.assert_called_once_with(module=Module.REPLICATION_MODULE,
        #                 func=Function.REPLICA_FLUSH)

        # Case 2 should return "No action" and call reset_v_change
        pred_module.reset_v_change = Mock()
        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 1, 2), ViewEstablishmentEnums.NO_ACTION)
        pred_module.reset_v_change.assert_any_call()

        # Case 3 should return "Reset"
        pred_module.reset_all = MagicMock(return_value = ViewEstablishmentEnums.RESET)
        self.assertEqual(pred_module.automation(ViewEstablishmentEnums.ACTION, 1, 3), ViewEstablishmentEnums.RESET)