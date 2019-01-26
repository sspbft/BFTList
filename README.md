# BFTList
[![Build status](https://travis-ci.org/practicalbft/BFTList.svg?branch=master)](https://travis-ci.org/travis-ci/travis-web)

List modeled as a replicated state machine based on failure detectors.

## Set up
First, make sure that you have [Python 3.5](https://www.python.org/downloads/), [pip3.5](https://pip.pypa.io/en/stable/installing/) and [virtualenv](https://pypi.org/project/virtualenv/) installed. Then, follow the commands below.

```
git clone https://github.com/practicalbft/BFTList.git && cd BFTList
virtualenv --python=$(which python3.5) ./env && source ./env/bin/activate
pip3.5 install -r requirements.txt
chmod +x start test
```

Note, if you're having problems with pip, one (or both) of the following commands might help.
```
pip install --upgrade pip
curl https://bootstrap.pypa.io/get-pip.py | python3
```

Now you can simply run `./start` and the server can be found on [localhost:5000](http://localhost:5000)! To kill the application, enter `CTRL + Z`.

### Linting
The code base is linted using [flake8](https://pypi.org/project/flake8/) with [pydocstyle](https://github.com/PyCQA/pydocstyle), so make sure to lint the code by running `flake8` before pushing any code.

### Testing
[unittest](https://docs.python.org/2/library/unittest.html) is setup so add appropriate unit tests in the `tests` folder (make sure the file ends with `_test.py`) and make sure that all tests pass by running `./test` before pushing any code.

### Travis integration
Both linting and testing is setup to be run for all Pull Requests and on each push to master by Travis.

## System description
Each node uses two ports: one for the API (default to `4000`) and one for the self-stabilizing communication channel with other nodes (`500{node_id}`). Node with id `1` would therefore be using ports `4000` and `5001` for example.
