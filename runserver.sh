#!/bin/sh

# For macOS: https://stackoverflow.com/a/52230415/78903
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Flask config
export FLASK_ENV="development"
export FLASK_RUN_HOST="${FLASK_RUN_HOST:=0.0.0.0}"
export FLASK_RUN_PORT="${FLASK_RUN_PORT:=3000}"
flask run
