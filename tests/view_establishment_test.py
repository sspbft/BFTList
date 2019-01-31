import unittest
from unittest.mock import Mock, MagicMock
from resolve.resolver import Resolver
from modules.view_establishment.predicates import PredicatesAndAction
from modules.view_establishment.module import ViewEstablishmentModule
from resolve.enums import Function, Module


class ViewEstablishmentModuleTest(unittest.TestCase):

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