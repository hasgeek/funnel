#!/bin/bash

# Load config into environment variables
set -o allexport
source .flaskenv
source .env
source .testenv
source .env.testing
set +o allexport

# Break on errors instead of continuing
set -o errexit

python -m tests.test_fixture_initdb
flask run -p 3002 --no-reload --debugger 2>&1 1>/tmp/funnel-server.log & echo $! > /tmp/funnel-server.pid
function killserver() {
    kill $(cat /tmp/funnel-server.pid)
    python -m tests.test_fixture_dropdb
    rm /tmp/funnel-server.pid
}
trap killserver INT
npx playwright test
killserver
