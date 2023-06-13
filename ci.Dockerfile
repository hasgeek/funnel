# syntax=docker/dockerfile:1.4

# Dockerfile syntax & features documentation:
# https://github.com/moby/buildkit/blob/master/frontend/dockerfile/docs/reference.md

FROM hasgeek/funnel-base-devtest
LABEL name="FunnelCI" version="0.1"
USER pn
RUN \
    mkdir -pv /home/pn/.npm /home/pn/app/node_modules /home/pn/.cache/pip \
    /home/pn/app/coverage /home/pn/.local

WORKDIR /home/pn/app
COPY --chown=pn:pn . .
ENTRYPOINT [ "/home/pn/app/docker/entrypoints/ci-test.sh" ]
