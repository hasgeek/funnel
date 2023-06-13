#!/bin/bash

chown pn:pn /home/pn/.npm /home/pn/.cache /home/pn/.cache/pip /home/pn/app \
    /home/pn/app/coverage /home/pn/.local
make install-test
pytest --allow-hosts=127.0.0.1,::1,$(hostname -i),$(getent ahosts db-test | awk '/STREAM/ { print $1}'),$(getent ahosts redis-test | awk '/STREAM/ { print $1}') --gherkin-terminal-reporter -vv --showlocals --cov=funnel
coverage lcov -o coverage/funnel.lcov
