# BFTList
[![Build status](https://travis-ci.org/practicalbft/BFTList.svg?branch=master)](https://travis-ci.org/travis-ci/travis-web)

List modeled as a replicated state machine based on failure detectors.

## Set up
First, make sure that you have [Python 3.5](https://www.python.org/downloads/), [pip3.5](https://pip.pypa.io/en/stable/installing/) and [virtualenv](https://pypi.org/project/virtualenv/) installed. Then, follow the commands below.

```
git clone https://github.com/practicalbft/BFTList.git && cd BFTList
virtualenv --python=$(which python3.5) ./env && source ./env/bin/activate
pip3.5 install -r requirements.txt
chmod +x start.sh
```

Note, if you're having problems with pip, one (or both) of the following commands might help.
```
pip install --upgrade pip
curl https://bootstrap.pypa.io/get-pip.py | python3
```

Now you can simple run `./start.sh` and the server can be found on [localhost:5000](http://localhost:5000)! To kill the application, enter `CTRL + Z`.

### Linting
The code base is linted using [flake8](https://pypi.org/project/flake8/) with [pydocstyle](https://github.com/PyCQA/pydocstyle), so make sure to lint the code by running `flake8` before pushing any code.

### Testing
[pytest](https://docs.pytest.org/en/latest/contents.html) is setup so add appropriate unit tests and make sure that all tests pass by running `PYTHONPATH=. pytest` before pushing any code.

### Travis integration
Both linting and testing is setup to be run for all Pull Requests and on each push to master by Travis.
