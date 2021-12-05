FROM vivekdurai/python-node-postgres:latest

# We don't want to run our application as root if it is not strictly necessary, even in a container.
# Create a user and a group called 'app' to run the processes.
# A system user is sufficient and we do not need a home.

RUN adduser --system --group --no-create-home app

# Make the directory the working directory for subsequent commands
WORKDIR app

COPY uwsgi.ini /etc/uwsgi/

# Place the application components in a dir below the root dir
COPY . /app/

RUN cd /app/funnel/assets; make

# Install from the requirements.txt we copied above
COPY requirements.txt /tmp
RUN pip install -r requirements.txt
COPY . /tmp/myapp
RUN pip install /tmp/myapp

# Hand everything over to the 'app' user
RUN chown -R app:app /app

# Subsequent commands, either in this Dockerfile or in a
# docker-compose.yml, will run as user 'app'
USER app


# We are done with setting up the image.
# As this image is used for different
# purposes and processes no CMD or ENTRYPOINT is specified here,
# this is done in docker-compose.yml.
