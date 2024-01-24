#!/bin/bash

# Load config into environment variables
set -o allexport
source .flaskenv
# shellcheck disable=SC1091
source .env
# shellcheck disable=SC1091
source .testenv
# shellcheck disable=SC1091
source .env.testing
set +o allexport

# Break on errors instead of continuing
set -o errexit

python -m tests.cypress.cypress_initdb_test
flask run -p 3002 --no-reload --debugger 1>/tmp/funnel-server.log 2>&1 & echo $! > /tmp/funnel-server.pid
function killserver() {
    kill "$(cat /tmp/funnel-server.pid)"
    python -m tests.cypress.cypress_dropdb_test
    rm /tmp/funnel-server.pid
}
trap killserver INT
npx --prefix tests/cypress cypress run --browser chrome
killserver
