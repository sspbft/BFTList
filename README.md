# BFTList
[![Build status](https://travis-ci.org/practicalbft/BFTList.svg?branch=master)](https://travis-ci.org/travis-ci/travis-web)

This repository contains code for a list modeled as a BFT replicated state machine based on failure detectors, hence the clever name BFTList. This application is part of our Master's thesis at Chalmers University of Technology, with the task of validating the algorithm proposed in [Self-Stabilizing Byzantine Tolerant Replicated State Machine Based on Failure Detectors]() written by [Shlomi Dolev](mailto:dolev@cs.bgu.ac.il), [Chryssis Georgiou](chryssis@cs.ucy.ac.cy), [Ioannis Marcoullis](imarcoullis@cs.ucy.ac.cy) and [Elad M. Schiller](mailto:elad@chalmers.se).

## Set up
First, make sure that you have [Python 3.7](https://www.python.org/downloads/) installed. Then, follow the commands below.

```
git clone https://github.com/practicalbft/BFTList.git && cd BFTList
python3.7 -m venv env
source ./env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Instructions for how to run this application without using [Thor](https://github.com/practicalbft/thor) (which you should not, since Thor was built for this exact use case) will be added later.

### Linting
The code base is linted using [flake8](https://pypi.org/project/flake8/) with [pydocstyle](https://github.com/PyCQA/pydocstyle), so make sure to lint the code by running `flake8` before pushing any code.

### Testing
[unittest](https://docs.python.org/2/library/unittest.html) is setup so add appropriate unit tests in the `tests` folder (make sure the file ends with `_test.py`) and make sure that all tests pass by running `./test` before pushing any code.

### Travis integration
Both linting and testing is setup to be run for all Pull Requests and on each push to master by Travis.

## System description
Each node uses two ports: one for the API (default to `4000`) and one for the self-stabilizing communication channel with other nodes (`500{node_id}`). Node with id `1` would therefore be using ports `4001`, `5001` and `6001` for example.

### Ports
BFTList uses three ports (for now) to be able to run with full functionality. 

| Port number   | Service                       | 
| ------------- |:-----------------------------:|
| 400{ID}       | REST API                      |
| 500{ID}       | Inter-node communication      |
| 600{ID}       | Prometheus metrics endpoint   |