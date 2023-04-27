# syntax=docker/dockerfile:1.4

ARG BASE_PYTHON_VERSION=3.7

FROM python:${BASE_PYTHON_VERSION}-slim

ARG BASE_NODE_VERSION=18
RUN groupadd --gid 1000 funnel && useradd --uid 1000 --gid funnel --shell /bin/bash --create-home funnel
COPY docker/.npmrc /usr/local/etc/npmrc
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/root/.npm <<EOF
apt-get update -yqq
apt-get upgrade -yqq
apt-get install -yqq curl gcc g++ make git
curl -fsSL https://deb.nodesource.com/setup_${BASE_NODE_VERSION}.x | bash - &&
apt-get install -yqq nodejs && npm install npm@latest -g
# Uninstalling gcc, g++ and their deps saves around 200+ MB in the image size of this layer
# But, commenting them out for now, since we are not able to compile uwsgi during pip install
# apt-get remove -yqq gcc g++ curl
apt-get autoclean -yqq
apt-get autoremove -yqq
rm -rf /tmp/*
EOF
