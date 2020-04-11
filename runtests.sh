#!/bin/bash
set -e
export FLASK_ENV="TESTING"
if [ -f secrets.test ]; then
	source ./secrets.test
fi
coverage run -m pytest "$@"
coverage report -m
