import unittest
import os
from conf import config

class TestConfig(unittest.TestCase):
    def test_config_can_parse_nodes_txt(self):
        s = "0,localhost,127.0.0.1,5000\n1,localhost,127.0.0.1,5001\n"
        path = "conf/tmp.txt"
        with open(path, "w") as f:
            f.write(s)
        hosts = config.get_nodes(hosts_path=path)
        self.assertEqual(len(hosts.values()), 2)
        self.assertEqual(hosts[0].id, 0)
        self.assertEqual(hosts[0].hostname, "localhost")
        self.assertEqual(hosts[0].ip, "127.0.0.1")
        self.assertEqual(hosts[0].port, 5000)
        self.assertEqual(hosts[1].id, 1)
        os.remove(path)

if __name__ == '__main__':
    unittest.main()