#!/bin/bash

# https://github.com/docker/for-mac/issues/5480

chown -R pn:pn /home/pn/.npm /home/pn/.cache /home/pn/.cache/pip /home/pn/app \
    /home/pn/app/coverage /home/pn/.local
