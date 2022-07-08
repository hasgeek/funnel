#!/bin/bash
set -e
export FLASK_ENV="TESTING"
if [ $# -eq 0 ]; then
    pytest --cov=funnel
else
    pytest "$@"
fi
