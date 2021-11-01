from urllib.parse import urlsplit

from funnel import app

REDIS_URL = app.config.get('REDIS_URL', 'redis://redis:6379/0')

# REDIS_URL is not taken by setup_default_arguments function of rq/scripts/__init__.py
# so, parse that into pieces and give it

r = urlsplit(REDIS_URL)
REDIS_HOST = r.hostname
REDIS_PORT = r.port
REDIS_PASSWORD = r.password
REDIS_DB = 0
