#!/bin/bash
set -e
# Put Flask in testing mode
export FLASK_ENV="TESTING"
# Provide a HOSTALIASES file for platforms that support it
export HOSTALIASES="$(cd $(dirname $0); pwd -P)/HOSTALIASES"
# For macOS: https://stackoverflow.com/a/52230415/78903
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
if [ $# -eq 0 ]; then
    pytest --cov=funnel
else
    pytest "$@"
fi
