"""Gunicorn configuration."""

import multiprocessing
import os

from dotenv import load_dotenv

workers = 2 * multiprocessing.cpu_count() + 1

# TODO: If multiple entry paths depend on reading .env, maybe it should be part of the
# app init and not reproduced in each place separately
for env_file in ('.env', '.flaskenv'):
    env = os.path.join(os.getcwd(), env_file)
    if os.path.exists(env):
        load_dotenv(env)
