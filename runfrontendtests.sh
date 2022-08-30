#!/bin/bash
set -e
export FLASK_ENV=testing

# For macos: https://stackoverflow.com/a/52230415/78903
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

python -m tests.cypress.frontend_tests_initdb
flask run -p 3002 --no-reload --debugger 2>&1 1>/tmp/funnel-server.log & echo $! > /tmp/funnel-server.pid
function killserver() {
    kill $(cat /tmp/funnel-server.pid)
    python -m tests.cypress.frontend_tests_dropdb
    rm /tmp/funnel-server.pid
}
trap killserver INT
cd tests/cypress
npx cypress run --browser chrome
killserver
