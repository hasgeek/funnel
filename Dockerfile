# syntax=docker/dockerfile:1.4

# https://github.com/moby/buildkit/blob/master/frontend/dockerfile/docs/reference.md

FROM node:lts-alpine as assets
USER node
WORKDIR /home/node/app
RUN mkdir -pv /home/node/app/funnel/static/build /home/node/app/funnel/static/build_cache
COPY --chown=node:node package.json package-lock.json ./
RUN --mount=type=cache,target=/home/node/.npm/,uid=1000,gid=1000 npm ci
COPY --chown=node:node ./funnel/assets/ ./funnel/assets/
COPY --chown=node:node webpack.config.js .eslintrc.js ./
RUN --mount=type=cache,target=/home/node/app/.webpack_cache/,uid=1000,gid=1000 \
    --mount=type=cache,target=/home/node/app/funnel/static/build_cache/,uid=1000,gid=1000 \
    cp -R funnel/static/build_cache funnel/static/build \
    && npm run build \
    && cp -R funnel/static/build funnel/static/build_cache \
    && cp -R funnel/static/build funnel/static/built

FROM python:3.11-bullseye as app
LABEL maintainer="Hasgeek"
RUN chsh -s /usr/sbin/nologin root
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update -yqq \
    && apt-get install -yqq --no-install-recommends supervisor \
    && apt-get autoclean -yqq \
    && apt-get autoremove -yqq \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -pv /var/log/supervisor
COPY ./docker/supervisord/supervisord.conf /etc/supervisor/supervisord.conf
RUN addgroup --gid 1000 funnel && adduser --uid 1000 --gid 1000 funnel
ENV PATH "$PATH:/home/funnel/.local/bin"
USER funnel
WORKDIR /home/funnel/app

COPY --chown=funnel:funnel Makefile Makefile
COPY --chown=funnel:funnel requirements/base.txt requirements/base.txt
RUN --mount=type=cache,target=/home/funnel/.cache/pip,uid=1000,gid=1000 make install-python

COPY --chown=funnel:funnel . .
COPY --from=assets --chown=funnel:funnel /home/node/app/funnel/static/built/ funnel/static/build
RUN mkdir -pv /home/funnel/app/logs
ENTRYPOINT [ "uwsgi", "--ini" ]

FROM app as ci
USER root
ENV PYTHONUNBUFFERED=1
RUN mkdir -pv /home/funnel/app/coverage && chown -R funnel:funnel /home/funnel/.cache /home/funnel/app/coverage
# hadolint ignore=DL3008,DL4006,SC2046
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update -yqq \
    && apt-get install -yqq --no-install-recommends xvfb firefox-esr \
    && apt-get autoclean -yqq \
    && apt-get autoremove -yqq \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL $(curl -fsSL https://api.github.com/repos/mozilla/geckodriver/releases/latest \
    | grep browser_download_url \
    | grep 'linux64.tar.gz\"' \
    | grep -o 'http.*\.gz') \
    | tar -xvz -C /usr/local/bin
USER funnel
COPY --chown=funnel:funnel requirements/base.txt requirements/test.txt ./requirements/
RUN --mount=type=cache,target=/home/funnel/.cache/pip,uid=1000,gid=1000 make install-python-test
ENTRYPOINT [ "/home/funnel/app/docker/entrypoints/ci.sh" ]
