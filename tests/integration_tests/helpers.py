import asyncio
import os
import json
import requests
import psutil
import time
import warnings
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import conf.config
import subprocess

HOST = "http://localhost"
BASE_PORT = 4000
N = 6
F = 1
RELATIVE_PATH_FIXTURES_HOST = "./tests/fixtures/hosts.txt"
start_state_file_path = os.path.abspath("./conf/start_state.json")
MAX_NODE_CALLS = 10

def suppress_warnings(test_func):
    def do_test(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            test_func(self, *args, **kwargs)
    return do_test

def run_coro(coro):
    """Runs a co-routing in the default event loop and retuns it result."""
    return asyncio.get_event_loop().run_until_complete(coro)

def get_nodes():
    """Helper method to get fixed set of nodes for integration tests."""
    return conf.config.get_nodes(RELATIVE_PATH_FIXTURES_HOST)

# HTTP related helpers
def session():
    """Sets up a HTTP session with a retry policy."""
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=0.5)
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

async def GET(node_id, path):
    """GETs data from a nodes and returns the result to the caller."""
    r = session().get(f"{HOST}:{BASE_PORT + node_id}{path}")
    if r.status_code != 200:
        raise ValueError(f"Got bad response {r.status_code} from url {url}.")
    return {"status_code": r.status_code, "data": r.json()}


# application runner helpers
async def launch_bftlist(test_name="unknown test", args={}):
    """Launches BFTList for integration testing."""
    nodes = get_nodes()
    cmd = ". env/bin/activate && python3.7 main.py"
    cwd = os.path.abspath(".")
    pids = []

    for node_id in nodes.keys():
        env = os.environ.copy()
        env["ID"] = str(node_id)
        env["API_PORT"] = str(4000 + node_id)
        env["NUMBER_OF_NODES"] = str(N)
        env["NUMBER_OF_BYZANTINE"] = str(F)
        env["NUMBER_OF_CLIENTS"] = "1"
        env["HOSTS_PATH"] = os.path.abspath(RELATIVE_PATH_FIXTURES_HOST)
        env["INTEGRATION_TEST"] = test_name

        if "BYZANTINE" in args:
            if node_id in args["BYZANTINE"]["NODES"]:
                env["BYZANTINE"] = "true"
                env["BYZANTINE_BEHAVIOR"] = args["BYZANTINE"]["BEHAVIOR"]

        p = subprocess.Popen(cmd, shell=True, cwd=cwd, env=env)
        pids.append(p.pid)

    await asyncio.sleep(2)  # give nodes time to start before returning
    return pids


def kill(pids):
    """Kills all processes in the supplied list containing PIDs."""
    for pid in pids:
        process = psutil.Process(pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()
    return

def cleanup():
    """Removes all generated state files after test and cleans up."""
    try:
        os.remove(start_state_file_path)
    except FileNotFoundError:
        pass
    time.sleep(1)

# IO
def write_state_conf_file(state):
    """Dumps a dict to a json file used to inject state to modules."""
    with open(f"{start_state_file_path}", "w") as outfile:
        json.dump(state, outfile)