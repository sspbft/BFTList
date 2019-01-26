import unittest
from unittest.mock import Mock, MagicMock
from modules.view_establishment.predicates import PredicatesAndAction
from modules.view_establishment.module import ViewEstablishmentModule


# TODO implement more tests
class TestPredicatesAndAction(unittest.TestCase):

    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')

    def test_predicate_can_be_initialized(self):
       # monkeypatch.setattr(ViewEstablishmentModule,'moduleMock')
        mock = Mock(ViewEstablishmentModule)
        module = PredicatesAndAction(mock)
        self.assertTrue(module)

    #def test_interface_get_view(self):
        #monkeypatch.setattr(ViewEstablishmentModule,'moduleMock')
        #monkeypatch.setattr(ViewEstablishmentModule.phs,'phaseMock',[0,0])
       # mock = Mock(ViewEstablishmentModule)
       # module = PredicatesAndAction(mock)
       # module.get_view = MagicMock(return_vale = 0 )
        # Own view
       # assert module.get_view(0) == 0

if __name__ == '__main__':
    unittest.main()