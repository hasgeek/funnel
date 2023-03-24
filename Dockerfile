# Base image from https://hub.docker.com/r/nikolaik/python-nodejs
FROM nikolaik/python-nodejs:latest

# install base+build packages
RUN apt-get -y install curl git wget unzip build-essential make postgresql libpq-dev python-dev

# Python-nodejs includes a `pn` user, which we'll use.
USER pn
WORKDIR /home/pn/app

COPY uwsgi.ini /etc/uwsgi/

# Place the application components in a dir below the root dir
COPY . /app/

RUN cd /app/funnel/assets; make

# Install from the requirements.txt we copied above
COPY requirements.txt /tmp
RUN pip install -r requirements.txt
COPY . /tmp/myapp
RUN pip install /tmp/myapp

# We are done with setting up the image.
# As this image is used for different
# purposes and processes no CMD or ENTRYPOINT is specified here,
# this is done in docker-compose.yml.
