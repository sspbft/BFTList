import unittest
from unittest.mock import Mock, MagicMock, call
from resolve.resolver import Resolver
from modules.view_establishment.predicates import PredicatesAndAction
from modules.view_establishment.module import ViewEstablishmentModule
from modules.enums import ViewEstablishmentEnums
from resolve.enums import Function, Module


class ViewEstablishmentModuleTest(unittest.TestCase):
    
    # While true loop

    def test_while_true_case_1_is_true_and_return_is_an_action(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)

        # (1)Predicates and action reset all should be called
        view_est_mod.pred_and_action.need_reset = MagicMock(return_value = True)
        view_est_mod.pred_and_action.reset_all = Mock()

        # (2) Processor i recent values are noticed and both processors have been witnessed 
        view_est_mod.noticed_recent_value = MagicMock(return_value = True)
        view_est_mod.get_witnesses = MagicMock(return_value = {0,1})

        # (3)Let predicate of case 0 be false and case 1 true
        view_est_mod.witnes_seen = MagicMock(return_value = True)
        view_est_mod.pred_and_action.automation = MagicMock(side_effect=(lambda t ,y, x: x))

        # (4) Mocks the final calls
        view_est_mod.next_phs = Mock()
        view_est_mod.send_msg = Mock()

        # Run the method and check all statements above
        view_est_mod.run()

        # (1) Predicates and action reset all should be called
        view_est_mod.pred_and_action.reset_all.assert_any_call()

        # (2) Processor i recent values are noticed and both processors have been witnessed 
        self.assertTrue(view_est_mod.witnesses[view_est_mod.id])
        self.assertEqual(view_est_mod.witnesses_set, {0,1})

        # (3) Let predicate of case 0 be false and case 1 true, make sure function is called 
        calls_automaton = [call(
            ViewEstablishmentEnums.PREDICATE,view_est_mod.phs[view_est_mod.id], 0),
            call(
            ViewEstablishmentEnums.PREDICATE,view_est_mod.phs[view_est_mod.id], 1),
            call(
            ViewEstablishmentEnums.ACTION,view_est_mod.phs[view_est_mod.id], 1)
            ]
        # any_order means that no other calls to the function should be made
        view_est_mod.pred_and_action.automation.assert_has_calls(calls_automaton, any_order = False)

        # (4) Check that the functions are called with correct input
        view_est_mod.next_phs.assert_called_once()
        calls_send_msg = [call(0), call(1)]
        view_est_mod.send_msg.assert_has_calls(calls_send_msg, any_order = False)

    # Used for mocking predicate_and_action automaton for different values
    # When called with predicate : case 0 returns false, case 1 returns true.
    def side_effect_case_1_return_no_action(self, action, phase, case):
        if(action == ViewEstablishmentEnums.ACTION):
            return ViewEstablishmentEnums.NO_ACTION
        else: 
            return case

    def test_while_true_case_1_is_true_and_return_is_no_action(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)

        # (1)Predicates and action reset all should be called
        view_est_mod.pred_and_action.need_reset = MagicMock(return_value = True)
        view_est_mod.pred_and_action.reset_all = Mock()

        # (2) Processor i recent values are noticed and both processors have been witnessed 
        view_est_mod.noticed_recent_value = MagicMock(return_value = False)
        view_est_mod.get_witnesses = MagicMock(return_value = set())

        # (3)Let predicate of case 0 be false and case 1 true
        view_est_mod.witnes_seen = MagicMock(return_value = True)
        view_est_mod.pred_and_action.automation = MagicMock(side_effect=self.side_effect_case_1_return_no_action)

        # (4) Mocks the final calls
        view_est_mod.next_phs = Mock()
        view_est_mod.send_msg = Mock()

        # Run the method and check all statements above
        view_est_mod.run()

        # (3) Let predicate of case 0 be false and case 1 true, make sure function is called 
        calls_automaton = [call(
            ViewEstablishmentEnums.PREDICATE,view_est_mod.phs[view_est_mod.id], 0),
            call(
            ViewEstablishmentEnums.PREDICATE,view_est_mod.phs[view_est_mod.id], 1),
            call(
            ViewEstablishmentEnums.ACTION,view_est_mod.phs[view_est_mod.id], 1)
            ]
        # any_order means that no other calls to the function should be made
        view_est_mod.pred_and_action.automation.assert_has_calls(calls_automaton, any_order = False)

        # (4) Check that the functions are called with correct input
        view_est_mod.next_phs.assert_not_called()

        calls_send_msg = [call(0), call(1)]
        view_est_mod.send_msg.assert_has_calls(calls_send_msg, any_order = False)
        
    def test_while_true_no_case_is_true(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)

        # (1)Predicates and action reset all should not be called
        view_est_mod.pred_and_action.need_reset = MagicMock(return_value = False)
        view_est_mod.pred_and_action.reset_all = Mock()

        # (2) Processor i recent values are noticed and both processors have been witnessed 
        view_est_mod.noticed_recent_value = MagicMock(return_value = True)
        view_est_mod.get_witnesses = MagicMock(return_value = {0,1})

        # (3) No predicate is true
        view_est_mod.witnes_seen = MagicMock(return_value = True)
        view_est_mod.pred_and_action.automation = MagicMock(return_value = False)

        # (4) Mocks the final calls
        view_est_mod.next_phs = Mock()
        view_est_mod.send_msg = Mock()

        # Run the method and check all statements above
        view_est_mod.run()

        # (1) Predicates and action reset all should not be called
        view_est_mod.pred_and_action.reset_all.assert_not_called()

        # (3) 
        calls_automaton = [call(
            ViewEstablishmentEnums.PREDICATE,view_est_mod.phs[view_est_mod.id], 0),
            call(
            ViewEstablishmentEnums.PREDICATE,view_est_mod.phs[view_est_mod.id], 1),
            call(
            ViewEstablishmentEnums.PREDICATE,view_est_mod.phs[view_est_mod.id], 2),
            call(
            ViewEstablishmentEnums.PREDICATE,view_est_mod.phs[view_est_mod.id], 3)
            ]
        view_est_mod.pred_and_action.automation.assert_has_calls(calls_automaton, any_order = False)

        # (4) Check that next_phs is not called and send_msg are called with correct arguments
        view_est_mod.next_phs.assert_not_called()
        calls_send_msg = [call(0), call(1)]
        view_est_mod.send_msg.assert_has_calls(calls_send_msg, any_order = False)

    # Macros

    def test_echo_no_witn(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)

        # Both conditions are fulfilled
        view_est_mod.phs[view_est_mod.id] = 0
        view_est_mod.get_view = MagicMock(return_value = {"current": 0, "next": 1})
        view_est_mod.echo[1] = {view_est_mod.VIEWS: {"current": 0, "next": 1}, view_est_mod.PHASE: 0, view_est_mod.WITNESSES: None}
        self.assertTrue(view_est_mod.echo_no_witn(1))

        # The view in the echo is not correct
        view_est_mod.echo[1] = {view_est_mod.VIEWS: {"current": 0, "next": 0}, view_est_mod.PHASE: 0, view_est_mod.WITNESSES: None}
        self.assertFalse(view_est_mod.echo_no_witn(1))

        # The phase in the echo is not correct
        view_est_mod.echo[1] = {view_est_mod.VIEWS: {"current": 0, "next": 1}, view_est_mod.PHASE: 1, view_est_mod.WITNESSES: None}
        self.assertFalse(view_est_mod.echo_no_witn(1))

    def test_witnes_seen(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)

        # Both condition fulfilled with f = 0
        view_est_mod.witnesses[view_est_mod.id] = True
        view_est_mod.witnesses_set = {1}
        view_est_mod.echo[0] = {view_est_mod.VIEWS: {"current": 0, "next": 1}, view_est_mod.PHASE: 1, view_est_mod.WITNESSES: None}
        view_est_mod.echo[1] = {view_est_mod.VIEWS: {"current": 0, "next": 1}, view_est_mod.PHASE: 1, view_est_mod.WITNESSES: None}
        self.assertTrue(view_est_mod.witnes_seen())

        # Processor i has not been witnessed
        view_est_mod.witnesses[view_est_mod.id] = False
        self.assertFalse(view_est_mod.witnes_seen())

        # f = 1, meaning the set is not big enough, set = 2 and 5 is needed
        view_est_mod.number_of_byzantine = 1
        view_est_mod.witnesses[view_est_mod.id] = True
        self.assertFalse(view_est_mod.witnes_seen())


    def test_next_phs(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        view_est_mod.phs[view_est_mod.id] = 0

        # Move to phase 1
        view_est_mod.next_phs()
        self.assertEqual(view_est_mod.phs[view_est_mod.id], 1)

        # Move to phase 2
        view_est_mod.next_phs()
        self.assertEqual(view_est_mod.phs[view_est_mod.id], 0)

    # Interface functions

    def test_get_phs(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        view_est_mod.phs = [0, 1]
        self.assertEqual(view_est_mod.get_phs(0), 0)
        self.assertEqual(view_est_mod.get_phs(1), 1)

    def test_init(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        view_est_mod.phs = [0, 1]
        view_est_mod.witnesses_set = {0}
        view_est_mod.witnesses = [True, True]

        view_est_mod.init_module()
        self.assertEqual(view_est_mod.phs, [0, 0])
        self.assertEqual(view_est_mod.witnesses_set, set())
        self.assertEqual(view_est_mod.witnesses, [False, False])

    # Function added for while true loop

    def test_noticed_recent_value(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)

        # All have noticed
        view_est_mod.echo_no_witn = MagicMock(return_value = True)
        self.assertTrue(view_est_mod.noticed_recent_value())

        # Processor 1 has not noticed (0 False, 1 True)
        view_est_mod.echo_no_witn = MagicMock(side_effect=lambda x: not x)
        self.assertTrue(view_est_mod.noticed_recent_value())

        # None have noticed
        view_est_mod.echo_no_witn = MagicMock(return_value = False)
        self.assertFalse(view_est_mod.noticed_recent_value())

    def test_get_witnesses(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)

        # Both processors have been witnessed
        view_est_mod.witnesses=[True, True]
        self.assertEqual(view_est_mod.get_witnesses(), {0,1})

        # Both processor 1 has been witnessed, not processor 0
        view_est_mod.witnesses=[False, True]
        self.assertEqual(view_est_mod.get_witnesses(), {1})

        # None of the processors have been witnessed
        view_est_mod.witnesses=[False, False]
        self.assertEqual(view_est_mod.get_witnesses(), set())

    
    # Function added for re-routing inter-module communication
    def test_get_view_from_predicts_and_action(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        view_est_mod.pred_and_action.get_view = Mock()
        view_est_mod.get_view(0)
        view_est_mod.pred_and_action.get_view.assert_called_once_with(0)
    
    def test_allow_service_from_predicts_and_action(self):
        resolver = Resolver()
        view_est_mod = ViewEstablishmentModule(resolver)
        view_est_mod.pred_and_action.allow_service = Mock()
        view_est_mod.allow_service()
        view_est_mod.pred_and_action.allow_service.assert_any_call()