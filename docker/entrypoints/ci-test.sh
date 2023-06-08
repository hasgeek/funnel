#!/bin/bash

if [[ -f ".ci-cache/files/.eslintcache" ]]
then
    cp .ci-cache/files/.eslintcache .eslintcache
fi
make install-test
pytest --gherkin-terminal-reporter -vv --showlocals --cov=funnel
coverage lcov -o coverage/funnel.lcov
cp .ci-cache/files/.eslintcache .eslintcache
