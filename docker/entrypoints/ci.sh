#!/bin/bash

set -e

pytest \
    --allow-hosts=127.0.0.1,::1,$(hostname -i),$(getent ahosts $DB_HOST | awk '/STREAM/ { print $1}'),$(getent ahosts $REDIS_HOST | awk '/STREAM/ { print $1}') \
    --gherkin-terminal-reporter -vv --showlocals --cov=funnel $@
coverage lcov -o coverage/funnel.lcov
