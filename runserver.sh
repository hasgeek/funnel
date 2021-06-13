#!/bin/sh
export FLASK_ENV=development
export FLASK_RUN_HOST="${FLASK_RUN_HOST:=0.0.0.0}"
export FLASK_RUN_PORT="${FLASK_RUN_PORT:=3000}"
flask run
