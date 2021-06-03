#!/bin/bash
set -e
export PYTHONIOENCODING="UTF-8"
export FLASK_ENV=testing
if [ -f secrets.test ]; then
        source ./secrets.test
fi
python -m tests.e2e.frontend_tests_initdb
nohup flask run -p 3002 2>&1 1>/dev/null & echo $! > /tmp/server.pid
nohup ./rq.sh 2>&1 1>/dev/null & echo $! > /tmp/rq.pid
cd funnel/assets
npx cypress run --browser chrome
kill -9 `cat /tmp/rq.pid`
kill -9 `cat /tmp/server.pid`
cd ../..
python -m tests.e2e.frontend_tests_dropdb
