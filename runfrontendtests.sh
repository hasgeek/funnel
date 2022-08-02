#!/bin/bash
set -e
export FLASK_ENV=testing

# For macos: https://stackoverflow.com/a/52230415/78903
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

if [ -f secrets.test ]; then
        source ./secrets.test
fi
python -m tests.e2e.frontend_tests_initdb
nohup ./testserver.py 2>&1 1>/tmp/funnel-server.log & echo $! > /tmp/funnel-server.pid
nohup ./rq.sh 2>&1 1>/tmp/funnel-rq.log & echo $! > /tmp/funnel-rq.pid
cd funnel/assets
npx cypress run --browser chrome
kill `cat /tmp/funnel-server.pid /tmp/funnel-rq.pid`
# This doesn't always kill the processes, so try again
kill `ps -xww | grep flask | cut -f1 -d' '` 2> /dev/null
cd ../..
python -m tests.e2e.frontend_tests_dropdb
