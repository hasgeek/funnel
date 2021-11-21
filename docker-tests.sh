#!/bin/bash
set -e
export FLASK_ENV="TESTING"

psql postgresql://postgres:5432/postgres -c 'create database funnel_testing;'
flask dbconfig | sudo -u postgres psql funnel_testing
psql  postgresql://postgres:5432/postgres -c 'create database geoname_testing;'
flask dbconfig | sudo -u postgres psql geoname_testing

if [ -f secrets.test ]; then
	source ./secrets.test
fi
if [ $# -eq 0 ]; then
    pytest --cov=funnel
else
    pytest "$@"
fi
