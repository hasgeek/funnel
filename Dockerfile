# syntax=docker/dockerfile:1.4

ARG BASE_PYTHON_VERSION=3.7
ARG BASE_NODE_VERSION=18

FROM hasgeek/funnel-builder:python-${BASE_PYTHON_VERSION}-node-${BASE_NODE_VERSION}
USER funnel
WORKDIR /home/funnel/app

ENV PATH "$PATH:/home/funnel/.local/bin"

COPY --chown=funnel:funnel Makefile Makefile
COPY --chown=funnel:funnel package.json package.json
COPY --chown=funnel:funnel package-lock.json package-lock.json
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/home/funnel/.npm,uid=1000,gid=1000 \
    --mount=type=cache,target=/home/funnel/app/node_modules,uid=1000,gid=1000 npm install

RUN make deps-editable

COPY --chown=funnel:funnel requirements requirements
RUN --mount=type=cache,target=/home/funnel/.cache/pip,uid=1000,gid=1000 <<EOF
pip install --upgrade pip
pip install --use-pep517 -r requirements/base.txt
EOF

COPY --chown=funnel:funnel . .
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/home/funnel/.npm,uid=1000,gid=1000 \
    --mount=type=cache,target=/home/funnel/app/node_modules,uid=1000,gid=1000 npm run build
