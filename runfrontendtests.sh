#!/bin/sh
set -e
export PYTHONIOENCODING="UTF-8"
export FLASK_ENV="TESTING"
python -m tests.e2e.frontend_tests_initdb
nohup python runcypressserver.py > /dev/null 2>&1 & echo $! > /tmp/server.pid
nohup ./rq.sh > /dev/null 2>&1 & echo $! > /tmp/rq.pid
cd funnel/assets
npx cypress run --browser chrome
kill -9 `cat /tmp/rq.pid`
kill -9 `cat /tmp/server.pid`
cd ../..
python -m tests.e2e.frontend_tests_dropdb
