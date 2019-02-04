import asyncio
import os
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import conf.config
import subprocess

HOST = "http://localhost"
BASE_PORT = 4000
N = 5
F = 1

def run_coro(coro):
    """Runs a co-routing in the default event loop and retuns it result."""
    return asyncio.get_event_loop().run_until_complete(coro)

def get_nodes():
    """Helper method to get fixed set of nodes for integration tests."""
    return conf.config.get_nodes("./tests/integration_tests/fixtures/nodes.txt")

# HTTP related helpers
def session():
    """Sets up a HTTP session with a retry policy."""
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=0.5)
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

async def GET(node_id, path):
    """GETs data from a nodes and returns the result to the caller."""
    r = session().get(f"{HOST}:{BASE_PORT + node_id}")
    if r.status_code != 200:
        raise ValueError(f"Got bad response {r.status_code} from url {url}.")
    return {"status_code": r.status_code, "data": r.json()}

async def launch_bftlist():
    nodes = get_nodes()
    cmd = "source env/bin/activate && python3.7 main.py"
    cwd = os.path.abspath(".")
    for node_id in nodes.keys():
        env = os.environ.copy()
        env["ID"] = str(node_id)
        env["API_PORT"] = str(4000 + node_id)
        env["NUMBER_OF_NODES"] = N
        env["NUMBER_OF_BYZANTINE"] = F
        p = subprocess.Popen(cmd, shell=True, cwd=cwd, env=env)
        return p.pid

def kill(process):
    pass
