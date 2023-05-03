# syntax=docker/dockerfile:1.4

ARG BASE_PYTHON_VERSION=3.7
ARG BASE_NODE_VERSION=18

FROM nikolaik/python-nodejs:python${BASE_PYTHON_VERSION}-nodejs${BASE_NODE_VERSION}-bullseye

USER pn
WORKDIR /home/pn/app

ENV PATH "$PATH:/home/pn/.local/bin"

COPY --chown=pn:pn Makefile Makefile
COPY --chown=pn:pn package.json package.json
COPY --chown=pn:pn package-lock.json package-lock.json
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/home/pn/.npm,uid=1000,gid=1000 \
    --mount=type=cache,target=/home/pn/app/node_modules,uid=1000,gid=1000 npm install

RUN make deps-editable

COPY --chown=pn:pn requirements requirements
RUN --mount=type=cache,target=/home/pn/.cache/pip,uid=1000,gid=1000 <<EOF
pip install --upgrade pip
pip install --use-pep517 -r requirements/base.txt
EOF

COPY --chown=pn:pn . .
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/home/pn/.npm,uid=1000,gid=1000 \
    --mount=type=cache,target=/home/pn/app/node_modules,uid=1000,gid=1000 npm run build
