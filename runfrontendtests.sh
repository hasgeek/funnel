#!/bin/bash
set -e
export PYTHONIOENCODING="UTF-8"
export FLASK_ENV=testing
if [ -f secrets.test ]; then
        source ./secrets.test
fi
python -m tests.e2e.frontend_tests_initdb
