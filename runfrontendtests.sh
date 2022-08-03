#!/bin/bash
set -e
export FLASK_ENV=testing

# For macos: https://stackoverflow.com/a/52230415/78903
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

if [ -f secrets.test ]; then
        source ./secrets.test
fi
python -m tests.cypress.frontend_tests_initdb
nohup ./testserver.py 2>&1 1>/tmp/funnel-server.log & echo $! > /tmp/funnel-server.pid
cd funnel/assets
npx cypress run --browser chrome
kill `cat /tmp/funnel-server.pid`
cd ../..
python -m tests.cypress.frontend_tests_dropdb
