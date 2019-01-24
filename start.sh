#!/bin/bash

kill -9 $(lsof -i:5000 -t)
python main.py