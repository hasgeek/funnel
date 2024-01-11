"""Gunicorn default configuration."""
# The settings in this file may be overridden using env var `GUNICORN_CMD_ARGS` or
# directly on the command line to `gunicorn`

import multiprocessing

bind = '127.0.0.1:3000'
workers = 2 * multiprocessing.cpu_count() + 1
