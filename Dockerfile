# syntax=docker/dockerfile:1.4

FROM nikolaik/python-nodejs:python3.11-nodejs20-bullseye as base

# https://github.com/zalando/postgres-operator/blob/master/docker/logical-backup/Dockerfile
# https://stackoverflow.com/questions/68465355/what-is-the-meaning-of-set-o-pipefail-in-bash-script
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

LABEL Name=Funnel
LABEL Version=0.1

USER pn
RUN \
    mkdir -pv /home/pn/.cache/pip /home/pn/.npm /home/pn/tmp /home/pn/app /home/pn/app/coverage && \
    chown -R pn:pn /home/pn/.cache /home/pn/.npm /home/pn/tmp /home/pn/app /home/pn/app/coverage
EXPOSE 3000
WORKDIR /home/pn/app

ENV PATH "$PATH:/home/pn/.local/bin"

FROM base as devtest_base
USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update -yqq && \
    apt-get install -yqq --no-install-recommends lsb-release && \
    sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list' && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    apt-get update -yqq && apt-get upgrade -yqq && \
    echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections && \
    DEBIAN_FRONTEND=noninteractive apt-get install -yqq --no-install-recommends firefox-esr postgresql-client-15 && \
    cd /tmp/ && \
    curl -fsSL $(curl -fsSL https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep browser_download_url | grep 'linux64.tar.gz\"'| grep -o 'http.*\.gz') > gecko.tar.gz && \
    tar -xvzf gecko.tar.gz && \
    rm gecko.tar.gz && \
    chmod +x geckodriver && \
    mv geckodriver /usr/local/bin && \
    apt-get autoclean -yqq && \
    apt-get autoremove -yqq && \
    cd /home/pn/app
USER pn

FROM base as assets
COPY --chown=pn:pn package.json package.json
COPY --chown=pn:pn package-lock.json package-lock.json
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/home/pn/.npm,uid=1000,gid=1000 npm ci
COPY --chown=pn:pn ./funnel/assets ./funnel/assets
COPY --chown=pn:pn .eslintrc.js .eslintrc.js
COPY --chown=pn:pn webpack.config.js webpack.config.js
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/home/pn/.npm,uid=1000,gid=1000 npm run build

FROM base as dev_assets
COPY --chown=pn:pn package.json package.json
COPY --chown=pn:pn package-lock.json package-lock.json
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/home/pn/.npm,uid=1000,gid=1000 npm install
COPY --chown=pn:pn ./funnel/assets ./funnel/assets
COPY --chown=pn:pn .eslintrc.js .eslintrc.js
COPY --chown=pn:pn webpack.config.js webpack.config.js
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/home/pn/.npm,uid=1000,gid=1000 npx webpack --mode development --progress

FROM base as deps
COPY --chown=pn:pn Makefile Makefile
RUN make deps-editable
COPY --chown=pn:pn requirements/base.txt requirements/base.txt
RUN --mount=type=cache,target=/home/pn/.cache/pip,uid=1000,gid=1000 \
    pip install --upgrade pip && \
    pip install --use-pep517 -r requirements/base.txt

FROM devtest_base as test_deps
COPY --chown=pn:pn Makefile Makefile
RUN make deps-editable
COPY --chown=pn:pn requirements/base.txt requirements/base.txt
COPY --chown=pn:pn requirements/test.txt requirements/test.txt
RUN --mount=type=cache,target=/home/pn/.cache/pip,uid=1000,gid=1000 pip install --use-pep517 -r requirements/test.txt

FROM devtest_base as dev_deps
COPY --chown=pn:pn Makefile Makefile
RUN make deps-editable
COPY --chown=pn:pn requirements requirements
RUN --mount=type=cache,target=/home/pn/.cache/pip,uid=1000,gid=1000 pip install --use-pep517 -r requirements/dev.txt
COPY --from=dev_assets --chown=pn:pn /home/pn/app/node_modules /home/pn/app/node_modules

FROM deps as production
COPY --chown=pn:pn . .
COPY --chown=pn:pn --from=assets /home/pn/app/funnel/static /home/pn/app/funnel/static
ENTRYPOINT ["uwsgi", "--ini"]

FROM production as supervisor
USER root
RUN \
    apt-get update -yqq && \
    apt-get install -yqq --no-install-recommends supervisor && \
    apt-get autoclean -yqq && \
    apt-get autoremove -yqq && \
    mkdir -pv /var/log/supervisor
COPY ./docker/supervisord/supervisord.conf /etc/supervisor/supervisord.conf
# COPY ./docker/uwsgi/emperor.ini /etc/uwsgi/emperor.ini
ENTRYPOINT ["/usr/bin/supervisord"]

FROM test_deps as test
ENV PWD=/home/pn/app
COPY --chown=pn:pn . .

COPY --chown=pn:pn --from=assets /home/pn/app/funnel/static /home/pn/app/funnel/static
ENTRYPOINT ["/home/pn/app/docker/entrypoints/ci-test.sh"]
FROM dev_deps as dev
RUN --mount=type=cache,target=/home/pn/.cache/pip,uid=1000,gid=1000 cp -R /home/pn/.cache/pip /home/pn/tmp/.cache_pip
RUN mv /home/pn/tmp/.cache_pip /home/pn/.cache/pip
COPY --chown=pn:pn --from=dev_assets /home/pn/app/funnel/static /home/pn/app/funnel/static
