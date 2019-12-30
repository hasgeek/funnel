#!/bin/sh
set -e
export PYTHONIOENCODING="UTF-8"
export FLASK_ENV="TESTING"
python -m funnel.assets.cypress.initdb
python runcypressserver.py &
