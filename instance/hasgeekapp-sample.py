SITE_TITLE = 'HasGeek App'
#: Lastuser client id
LASTUSER_CLIENT_ID = ''
#: Lastuser client secret
LASTUSER_CLIENT_SECRET = ''
LASTUSER_COOKIE_DOMAIN = ''
#: Flat pages
FLATPAGES_AUTO_RELOAD = False
FLATPAGES_EXTENSION = '.md'
ASSET_BASE_PATH = 'build'
ASSET_MANIFEST_PATH = "static/build/manifest.json"

SESSION_COOKIE_NAME = 'root_session'
DELETE_COOKIES = {
    'session': {'domain': '.hasgeekapp.local', 'without_dot': True},
    'root_session': {'domain': '.hasgeekapp.local', 'without_dot': False},
    }

