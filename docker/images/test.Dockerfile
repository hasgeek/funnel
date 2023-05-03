# syntax=docker/dockerfile:1.4

ARG BASE_PYTHON_VERSION=3.7
ARG BASE_NODE_VERSION=18

FROM funnel-test-base:python-${BASE_PYTHON_VERSION}-node-${BASE_NODE_VERSION} as funnel-test
USER pn
RUN --mount=type=cache,target=/home/pn/.cache/pip,uid=1000,gid=1000 make install-python-test
CMD [ "pytest" ]
