# BFTList
[![Build status](https://travis-ci.org/sspbft/BFTList.svg?branch=master)](https://travis-ci.org/travis-ci/travis-web)

This repository contains code for a list modeled as a BFT replicated state machine based on failure detectors, hence the clever name BFTList. This application is part of our Master's thesis at Chalmers University of Technology, with the task of validating the algorithm proposed in [Self-Stabilizing Byzantine Tolerant Replicated State Machine Based on Failure Detectors]() written by [Shlomi Dolev](mailto:dolev@cs.bgu.ac.il), [Chryssis Georgiou](chryssis@cs.ucy.ac.cy), [Ioannis Marcoullis](imarcoullis@cs.ucy.ac.cy) and [Elad M. Schiller](mailto:elad@chalmers.se).

This project was carried out as a Master's Thesis at Chalmers University of Technology during Spring 2019 by [Therese Petersson](https://github.com/TheresePetersson) and [Axel Niklasson](https://github.com/axelniklasson).

## Set up
First, make sure that you have [Python 3.7.2](https://www.python.org/downloads/) installed. Then, follow the commands below.

```
git clone https://github.com/practicalbft/BFTList.git && cd BFTList
python3.7 -m venv env
source ./env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
chmod +x ./scripts/*
```

Instructions for how to run this application without using [Thor](https://github.com/practicalbft/thor) (which you should not, since Thor was built for this exact use case) will be added later.

### Linting
The code base is linted using [flake8](https://pypi.org/project/flake8/) with [pydocstyle](https://github.com/PyCQA/pydocstyle), so make sure to lint the code by running `flake8` before pushing any code.

### Testing
[unittest](https://docs.python.org/2/library/unittest.html) is setup so add appropriate unit tests in the `tests/unit_tests` folder (make sure the file starts with `test_`) and appropriate integration tests in the `tests/integration_tests` folder. Tests can run as seen below.

```
./scripts/test              # runs all tests
./scripts/test unit         # runs only unit tests
./scripts/test it           # runs only integration tests
./scripts/test <pattern>    # runs all test files with a filename matching pattern
```

### Travis integration
Both linting and testing is setup to be run for all Pull Requests and on each push to master by Travis.

## System description
### Ports
Each running node uses four ports: one for exposing metrics to the Prometheus scraper (`300{node_id}`), one for the Web API (defaults to `400{node_id}`), one for the non-self-stabilizing communication channel over TCP/IP with other nodes (`500{node_id}`) and one for the self-stabilizing communication channel over UDP/IP (`700{node_id}`). Node with id `1` would therefore be using ports `3001`, `4001`, `5001` and `7001` for example.

| Port number   | Service                           | 
| ------------- |:---------------------------------:|
| 300{ID}       | Prometheus metrics endpoint       |
| 400{ID}       | REST API                          |
| 500{ID}       | TCP inter-node communication      |
| 700{ID}       | UDP inter-node communication      |
