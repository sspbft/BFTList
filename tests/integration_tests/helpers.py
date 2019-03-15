# standard
import asyncio
import os
import requests
import psutil
import time
import warnings
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import subprocess
import logging
import jsonpickle

# local
import conf.config

logger = logging.getLogger(__name__)

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
        raise ValueError(f"Got bad response {r.status_code} from " +
                         f"node {node_id} on {path}.")
    return {"status_code": r.status_code, "data": r.json()}


def generate_hosts_file(n, path="./tests/fixtures"):
    """Generates the hosts file to be used in the test."""
    with open(f"{path}/hosts.txt", "w") as f:
        for i in range(n):
            f.write(f"{i},localhost,127.0.0.1,{5000+i}\n")


# application runner helpers
async def launch_bftlist(test_name="unknown test", n=N, f=F, args={}):
    """Launches BFTList for integration testing."""
    generate_hosts_file(n)
    nodes = get_nodes()
    cmd = ". env/bin/activate && python3.7 main.py"
    cwd = os.path.abspath(".")
    pids = []

    for node_id in nodes.keys():
        env = os.environ.copy()
        env["ID"] = str(node_id)
        env["API_PORT"] = str(4000 + node_id)
        env["NUMBER_OF_NODES"] = str(n)
        env["NUMBER_OF_BYZANTINE"] = str(f)
        env["NUMBER_OF_CLIENTS"] = "1"
        env["HOSTS_PATH"] = os.path.abspath(RELATIVE_PATH_FIXTURES_HOST)
        env["INTEGRATION_TEST"] = test_name
        env["DEBUG"] = "1"
        if "FORCE_VIEW" in args:
            env["FORCE_VIEW"] = args["FORCE_VIEW"]
        if "ALLOW_SERVICE" in args:
            env["ALLOW_SERVICE"] = args["ALLOW_SERVICE"]
        if "FORCE_NO_VIEW_CHANGE" in args:
            env["FORCE_NO_VIEW_CHANGE"] = args["FORCE_NO_VIEW_CHANGE"]

        if "BYZANTINE" in args:
            if node_id in args["BYZANTINE"]["NODES"]:
                env["BYZANTINE"] = "true"
                env["BYZANTINE_BEHAVIOR"] = args["BYZANTINE"]["BEHAVIOR"]

        p = subprocess.Popen(cmd, shell=True, cwd=cwd, env=env)
        pids.append(p.pid)

    sec = os.getenv("INTEGRATION_TEST_SLEEP")
    logger.info("Test suite sleeping, awaiting node startup")
    await asyncio.sleep(int(sec) if sec is not None else 2)
    logger.info("Sleeping done, now resuming tests")
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
        outfile.write(jsonpickle.encode(state))

def get_json_for_r_log_entry(req, x_set):
    """Returns a dict used to match r_log entries returned through API."""
    return {
        "request": req.to_dct(),
        "x_set": x_set
    }