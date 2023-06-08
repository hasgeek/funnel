# syntax=docker/dockerfile:1.4

# Dockerfile syntax & features documentation:
# https://github.com/moby/buildkit/blob/master/frontend/dockerfile/docs/reference.md

FROM hasgeek/funnel-base-devtest
RUN mkdir -pv /home/pn/.npm /home/pn/app/node_modules /home/pn/.pip /home/pn/app/.webpack_cache /home/pn/app/.ci-cache/files /home/pn/app/coverage \
    chown -R pn:pn /home/pn/.npm /home/pn/app/node_modules /home/pn/.pip /home/pn/app/.webpack_cache /home/pn/app/.ci-cache/files /home/pn/app/coverage
USER pn
WORKDIR /home/pn/app
COPY --chown=pn:pn . .
