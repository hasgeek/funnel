#!/bin/bash
set -e
export FLASK_ENV="TESTING"
if [ -f secrets.test ]; then
	source ./secrets.test
fi
if [ $# -eq 0 ]; then
    pytest --cov=funnel
else
    pytest --no-cov "$@"
fi
