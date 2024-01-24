#!/bin/sh

make install-test
pytest "--allow-hosts=127.0.0.1,::1,$(hostname -i),$(getent ahosts db-test | awk '/STREAM/ { print $1}'),$(getent ahosts redis-test | awk '/STREAM/ { print $1}')" --gherkin-terminal-reporter -vv --showlocals --cov=funnel
coverage lcov -o coverage/funnel.lcov
