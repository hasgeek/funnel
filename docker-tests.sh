#!/bin/bash
set -e
export FLASK_ENV="TESTING"

retry() {
  max_attempts="$1"; shift
  seconds="$1"; shift
  cmd="$@"
  attempt_num=1

  until $cmd
  do
    if [ $attempt_num -eq $max_attempts ]
    then
      echo "Attempt $attempt_num failed and there are no more attempts left!"
      return 1
    else
      echo "Attempt $attempt_num failed! Trying again in $seconds seconds..."
      attempt_num=`expr "$attempt_num" + 1`
      sleep "$seconds"
    fi
  done
}

retry 5 1 psql postgresql://postgres@postgres:5432/postgres -c '\l' >/dev/null

echo >&2 "$(date +%Y%m%dt%H%M%S) Postgres is up - executing command"

psql postgresql://postgres@postgres:5432/postgres -c 'create database funnel_testing;'
#flask dbconfig | sudo -u postgres psql funnel_testing
psql  postgresql://postgres@postgres:5432/postgres -c 'create database geoname_testing;'
#flask dbconfig | sudo -u postgres psql geoname_testing

if [ -f secrets.test ]; then
	source ./secrets.test
fi
if [ $# -eq 0 ]; then
    pytest --cov=funnel
else
    pytest "$@"
fi
