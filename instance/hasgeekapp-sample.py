"""Sample configuration."""

#: The title of this site
SITE_TITLE = "Hasgeek"
#: Site id
SITE_ID = 'hasgeek'
#: Auth cookie domain (must be dot-prefixed to serve auth for subdomains)
LASTUSER_COOKIE_DOMAIN = '.funnel.test'
#: Session cookies must be domain-local
SESSION_COOKIE_DOMAIN = False
#: Ensure session cookie isn't shared with subdomains
SESSION_COOKIE_NAME = 'root_session'
