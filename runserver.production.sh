#!/bin/sh
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export FLASK_ENV="production"
export FLASK_RUN_HOST="${FLASK_RUN_HOST:=0.0.0.0}"
export FLASK_RUN_PORT="${FLASK_RUN_PORT:=3000}"
flask db upgrade
uwsgi --ini ./uwsgi.ini