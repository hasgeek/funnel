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

python -m tests.cypress.cypress_initdb_test
flask run -p 3002 --no-reload --debugger 2>&1 1>/tmp/funnel-server.log & echo $! > /tmp/funnel-server.pid
function killserver() {
    kill $(cat /tmp/funnel-server.pid)
    python -m tests.cypress.cypress_dropdb_test
    rm /tmp/funnel-server.pid
}
trap killserver INT
npx --prefix tests/cypress cypress run --browser chrome
killserver
