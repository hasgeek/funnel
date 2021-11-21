#!/bin/bash
set -e
export FLASK_ENV="TESTING"

echo '127.0.0.1  funnel.test' >> /etc/hosts
echo '127.0.0.1  f.test' >> /etc/hosts
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
