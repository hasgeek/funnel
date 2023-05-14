# syntax=docker/dockerfile:1.4

ARG BASE_PYTHON_VERSION=3.7
ARG BASE_NODE_VERSION=18

FROM nikolaik/python-nodejs:python${BASE_PYTHON_VERSION}-nodejs${BASE_NODE_VERSION}-bullseye

# TODO: https://stackoverflow.com/questions/68992799/warning-apt-key-is-deprecated-manage-keyring-files-in-trusted-gpg-d-instead
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked --mount=type=cache,target=/var/lib/apt,sharing=locked <<EOF
curl -L https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
apt-get update -yqq
apt-get upgrade -yqq
echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
DEBIAN_FRONTEND=noninteractive apt-get install firefox-esr -yqq
if apt-cache show postgresql-client-15 > /dev/null 2>&1 ; then
    apt-get install --no-install-recommends -y postgresql-client-15 ;
else
    apt-get install --no-install-recommends -y postgresql-client ;
fi
cd /tmp/
curl -fsSL $(curl -fsSL https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep browser_download_url | grep 'linux64.tar.gz\"'| grep -o 'http.*\.gz') > gecko.tar.gz
tar -xvzf gecko.tar.gz
rm gecko.tar.gz
chmod +x geckodriver
mv geckodriver /usr/local/bin
apt-get autoclean -yqq
apt-get autoremove -yqq
EOF
USER pn
RUN <<EOF
mkdir -p /home/pn/.cache/pip
chown -R pn:pn /home/pn/.cache
mkdir -p /home/pn/.npm
chown -R pn:pn /home/pn/.npm
mkdir /home/pn/app
chown pn:pn /home/pn/app
EOF
VOLUME [ "/home/pn/app" ]
VOLUME [ "/home/pn/app/node_modules" ]
WORKDIR /home/pn/app
COPY --chown=pn:pn Makefile Makefile
COPY --chown=pn:pn package.json package.json
COPY --chown=pn:pn package-lock.json package-lock.json
RUN --mount=type=cache,target=/home/pn/.npm,uid=1000,gid=1000 npm install

ENV PATH "$PATH:/home/pn/.local/bin"

COPY --chown=pn:pn requirements requirements

RUN make deps-editable
RUN --mount=type=cache,target=/home/pn/.cache/pip,uid=1000,gid=1000 <<EOF
pip install --upgrade pip
pip install --use-pep517 -r requirements/dev.txt
EOF
