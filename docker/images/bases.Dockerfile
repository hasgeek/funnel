# syntax=docker/dockerfile:1.4

# Dockerfile syntax & features documentation:
# https://github.com/moby/buildkit/blob/master/frontend/dockerfile/docs/reference.md

FROM nikolaik/python-nodejs:python3.11-nodejs20-bullseye as base

# https://github.com/zalando/postgres-operator/blob/master/docker/logical-backup/Dockerfile
# https://stackoverflow.com/questions/68465355/what-is-the-meaning-of-set-o-pipefail-in-bash-script
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

STOPSIGNAL SIGINT
ENV PATH "$PATH:/home/pn/.local/bin"

# Install postgresql-client-15
USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update -yqq \
    apt-get install -yqq --no-install-recommends lsb-release \
    sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list' \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    apt-get update -yqq && apt-get upgrade -yqq \
    apt-get install -yqq --no-install-recommends postgresql-client-15 \
    apt-get purge -yqq lsb-release \
    apt-get autoclean -yqq \
    apt-get autoremove -yqq
RUN mkdir -pv /var/cache/funnel && chown -R pn:pn /var/cache/funnel
USER pn

FROM base as base-devtest
# Install firefox & geckodriver
USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update -yqq \
    apt-get upgrade -yqq \
    echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections \
    DEBIAN_FRONTEND=noninteractive apt-get install -yqq --no-install-recommends firefox-esr \
    cd /tmp/ \
    curl -fsSL $(curl -fsSL https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep browser_download_url | grep 'linux64.tar.gz\"'| grep -o 'http.*\.gz') > gecko.tar.gz \
    tar -xvzf gecko.tar.gz \
    rm gecko.tar.gz \
    chmod +x geckodriver \
    mv geckodriver /usr/local/bin \
    apt-get autoclean -yqq \
    apt-get autoremove -yqq
