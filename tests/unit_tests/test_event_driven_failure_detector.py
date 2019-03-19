import unittest
from unittest.mock import Mock, MagicMock, call
from resolve.resolver import Resolver
from modules.event_driven_fd.module import EventDrivenFDModule
from modules.constants import K_ADMISSIBILITY_THRESHOLD as K
from resolve.enums import MessageType
from copy import deepcopy

N = 6
F = 1

class TestEventDrivenFailureDetector(unittest.TestCase):
    def setUp(self):
        self.resolver = Resolver(testing=True)
        self.module = EventDrivenFDModule(0, self.resolver, 6, 1)
    
    def build_msg(self, sender, token, owner):
        return {
            "type": MessageType.EVENT_DRIVEN_FD_MESSAGE,
            "sender": sender,
            "data": {
                "token": token,
                "owner_id": owner
            }
        }
    
    def test_run(self):
        self.module.broadcast = MagicMock()

        # inject valid counters, module should run through and set last_correct_processors
        # and increment counter
        self.module.counters = {n_id: K for n_id in range(1, N)}
        self.module.run(True)
        self.assertCountEqual({
            "token": 0,
            "correct_processors": [i for i in range(1, N)]
        }, self.module.last_correct_processors)
        self.assertEqual(self.module.counters, {n_id: 0 for n_id in range(1, N)})
        self.assertEqual(self.module.token, 1)
    
    def test_on_msg_recv(self):
        self.module.send_token = MagicMock()

        # counter for sender should be incremented when sending current token
        self.assertEqual(self.module.counters[3], 0)
        msg = self.build_msg(3, 0, 0)
        self.module.on_msg_recv(msg)
        self.assertEqual(self.module.counters[3], 1)
        self.assertEqual(self.module.send_token.call_count, 1)

        # counter should stay the same when sending invalid token
        self.assertEqual(self.module.counters[3], 1)
        msg = self.build_msg(3, -1, 0)
        self.module.on_msg_recv(msg)
        self.assertEqual(self.module.counters[3], 1)
        # should not send token back due to invalid token, call_count should be the same
        self.assertEqual(self.module.send_token.call_count, 1)

        # no counter should change when current processor is not owner
        old_counters = deepcopy(self.module.counters)
        msg = self.build_msg(3, 0, 1)
        self.module.on_msg_recv(msg)
        self.assertEqual(old_counters, self.module.counters)
        self.assertEqual(self.module.send_token.call_count, 2)
    
    def test_send_token(self):
        self.resolver.send_to_node = MagicMock()
        self.module.send_token(0, 1, 2)
        msg = self.build_msg(0, 1, 2)
        self.resolver.send_to_node.assert_called_once_with(0, msg, True)

    def test_get_correct_processors(self):
        # should return [] for 0 correct processors
        self.assertEqual(self.module.get_correct_processors(), [])

        # inject two correct processors, should return their IDs
        self.module.counters[0] = K
        self.module.counters[2] = K + 1
        self.assertCountEqual(self.module.get_correct_processors(), [0,2])
    
    def test_correct_processors_have_replied(self):
        # should be False since no processors have yet replied
        self.assertFalse(self.module.correct_processors_have_replied())

        # force n-2f processors to have acked K times, should now be true
        self.module.counters = {i: K for i in range(N - 2*F)}
        self.assertTrue(self.module.correct_processors_have_replied())
    
    def test_get_last_correct_processor(self):
        # TODO
        pass
    