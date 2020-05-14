#!/usr/bin/env bash

# Standard packages
pip install -U pip wheel

# Forked version of Babel-NG w/ Py3 support
pip install git+https://github.com/hasgeek/flask-babelhg.git

# Standard requirments.txt
pip install -r requirements.txt
