#!/bin/bash

pytest --gherkin-terminal-reporter -vv --showlocals --cov=funnel
coverage lcov -o coverage/funnel.lcov
