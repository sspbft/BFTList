import unittest
from unittest.mock import Mock, MagicMock
from resolve.resolver import Resolver
from modules.view_establishment.predicates import PredicatesAndAction
from modules.view_establishment.module import ViewEstablishmentModule
from resolve.enums import Function, Module


class ViewEstablishmentModuleTest(unittest.TestCase):
    
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