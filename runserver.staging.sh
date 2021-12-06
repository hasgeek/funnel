#!/bin/sh
set -e
# For macOS: https://stackoverflow.com/a/52230415/78903
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Flask config
export FLASK_ENV="development"
export FLASK_RUN_HOST="${FLASK_RUN_HOST:=0.0.0.0}"
export FLASK_RUN_PORT="${FLASK_RUN_PORT:=3000}"

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

flask db upgrade

flask run
