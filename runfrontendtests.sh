#!/bin/sh
set -e
export PYTHONIOENCODING="UTF-8"
export FLASK_ENV="TESTING"
python -m tests.e2e.frontend_tests_initdb
python runcypressserver.py &
SERVER_PID=$!
cd funnel/assets
npx cypress run --browser chrome
kill $SERVER_PID
