import unittest
from resolve.resolver import Resolver

# TODO implement more tests
class TestResolver(unittest.TestCase):
    def test_resolver_can_be_initialized(self):
        resolver = Resolver(testing=True)
        self.assertIsNotNone(resolver)
        self.assertIsNone(resolver.modules)

if __name__ == '__main__':
    unittest.main()
