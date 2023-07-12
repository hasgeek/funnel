"""gunicorn configuration."""

import multiprocessing
import os

from dotenv import load_dotenv

workers = 2 * multiprocessing.cpu_count() + 1

for env_file in ('.env', '.flaskenv'):
    env = os.path.join(os.getcwd(), env_file)
    if os.path.exists(env):
        load_dotenv(env)
