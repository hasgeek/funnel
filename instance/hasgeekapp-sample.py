#: The title of this site
SITE_TITLE = "Hasgeek"
#: Site id
SITE_ID = 'hasgeek'
#: Server name (required to generate URLs)
SERVER_NAME = 'funnel.test:3000'
#: Auth cookie domain (must be dot-prefixed to serve auth for subdomains)
LASTUSER_COOKIE_DOMAIN = '.funnel.test'
#: Session cookies must be domain-local
SESSION_COOKIE_DOMAIN = False
#: Ensure session cookie isn't shared with subdomains
SESSION_COOKIE_NAME = 'root_session'
#: Delete cookies that aren't supposed to be set here
DELETE_COOKIES = {
    'session': [None, '.funnel.test'],  # Delete from None only in hasgeekapp!
    'root_session': ['.funnel.test'],
}
