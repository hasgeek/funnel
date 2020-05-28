#!/bin/bash
set -e
export PYTHONIOENCODING="UTF-8"
export FLASK_ENV="TESTING"
if [ -f secrets.test ]; then
        source ./secrets.test
fi
python -m tests.e2e.frontend_tests_initdb
python runcypressserver.py &
SERVER_PID=$!
./rq.sh > /dev/null &
RQ_PID=$!
cd funnel/assets
npx cypress run --browser chrome
kill $SERVER_PID
kill $RQ_PID
python -m tests.e2e.frontend_tests_dropdb
