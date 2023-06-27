# syntax=docker/dockerfile:1.4

# Dockerfile syntax & features documentation:
# https://github.com/moby/buildkit/blob/master/frontend/dockerfile/docs/reference.md

FROM nikolaik/python-nodejs:python3.11-nodejs20-bullseye as base

# https://github.com/zalando/postgres-operator/blob/master/docker/logical-backup/Dockerfile
# https://stackoverflow.com/questions/68465355/what-is-the-meaning-of-set-o-pipefail-in-bash-script
SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

STOPSIGNAL SIGINT
ENV PATH "$PATH:/home/pn/.local/bin"

# Install postgresql-client-15
USER root:root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update -y \
    && apt-get install -y --no-install-recommends lsb-release \
    && echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && apt-get update -y && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends postgresql-client-15 \
    && apt-get purge -y lsb-release
RUN mkdir -pv /var/cache/funnel && chown -R pn:pn /var/cache/funnel
USER pn:pn

FROM base as base-devtest
# Install firefox & geckodriver
USER root:root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update -y \
    && apt-get upgrade -y \
    && echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends firefox-esr \
    && cd /tmp/ \
    && curl -fsSL $(curl -fsSL https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep browser_download_url | grep 'linux64.tar.gz\"'| grep -o 'http.*\.gz') > gecko.tar.gz \
    && tar -xvzf gecko.tar.gz \
    && rm gecko.tar.gz \
    && chmod +x geckodriver \
    && mv geckodriver /usr/local/bin
USER pn:pn
