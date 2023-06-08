#!/bin/bash

cp .ci-cache/files/.eslintcache .eslintcache
make install-test
pytest --gherkin-terminal-reporter -vv --showlocals --cov=funnel
coverage lcov -o coverage/funnel.lcov
cp .ci-cache/files/.eslintcache .eslintcache
