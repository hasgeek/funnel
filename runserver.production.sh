#!/bin/sh
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export FLASK_ENV="production"
uwsgi --ini ./uwsgi.ini