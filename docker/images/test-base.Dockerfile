# syntax=docker/dockerfile:1.4

ARG BASE_PYTHON_VERSION=3.7
ARG BASE_NODE_VERSION=18
FROM hasgeek/funnel:python-${BASE_PYTHON_VERSION}-node-${BASE_NODE_VERSION} as test-base
USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked --mount=type=cache,target=/var/lib/apt,sharing=locked <<EOF
apt-get update -yqq
apt-get upgrade -yqq
echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
DEBIAN_FRONTEND=noninteractive apt-get install firefox-esr postgresql-client -yqq
cd /tmp/
curl -fsSL $(curl -fsSL https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep browser_download_url | grep 'linux64.tar.gz\"'| grep -o 'http.*\.gz') > gecko.tar.gz
tar -xvzf gecko.tar.gz
rm gecko.tar.gz
chmod +x geckodriver
mv geckodriver /usr/local/bin
apt-get autoclean -yqq
apt-get autoremove -yqq
cd /home/pn/app
mkdir -p /home/pn/.cache/pip
chown -R pn:pn /home/pn/.cache
EOF
