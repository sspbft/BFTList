from resolver.resolver import Resolver

# TODO implement more tests
class TestResolver(object):
    def test_resolver_can_be_initialized(self):
        resolver = Resolver()
        assert not resolver is None
        assert resolver.modules is None
