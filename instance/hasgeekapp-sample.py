SITE_TITLE = 'Hasgeek App'
#: Lastuser client id
LASTUSER_CLIENT_ID = ''
#: Lastuser client secret
LASTUSER_CLIENT_SECRET = ''  # nosec  # noqa: S105
LASTUSER_COOKIE_DOMAIN = ''
#: Flat pages
FLATPAGES_AUTO_RELOAD = False
FLATPAGES_EXTENSION = '.md'
ASSET_BASE_PATH = 'build'
ASSET_MANIFEST_PATH = "static/build/manifest.json"

SESSION_COOKIE_NAME = 'root_session'
DELETE_COOKIES = {
    'session': (None, '.hasgeekapp.local'),
    'root_session': ('.hasgeekapp.local',),
}
