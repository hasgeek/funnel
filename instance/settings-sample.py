"""Sample configuration."""

# ==== BASIC SETUP ====

DEBUG = False
#: Site id (for statsd)
SITE_ID = 'hasgeek'
#: The title of this site
SITE_TITLE = 'Hasgeek Funnel'
#: Support contact email
SITE_SUPPORT_EMAIL = 'test@example.com'
#: Support contact phone
SITE_SUPPORT_PHONE = '+1 234 567 8901'
#: Timezone
TIMEZONE = 'Asia/Kolkata'
#: Used for attribution when sharing a proposal on twitter
TWITTER_ID = "hasgeek"
#: Log file
LOGFILE = 'error.log'
DASHBOARD_USERS = ['']
ENABLE_COMMENT_SIDEBAR = True


# ==== DB & CACHES ====

#: Database backend
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg://user:pass@host/database'
SQLALCHEMY_BINDS = {
    'geoname': 'postgresql+psycopg://user:pass@host/geoname',
}
CACHE_TYPE = 'redis'
REDIS_URL = RQ_REDIS_URL = RQ_DASHBOARD_REDIS_URL = 'redis://localhost:6379/0'
RQ_SCHEDULER_INTERVAL = 1


# ==== SECURITY ====

# Session config
SESSION_COOKIE_NAME = 'root_session'
SESSION_COOKIE_DOMAIN = False
SESSION_COOKIE_SECURE = True
PREFERRED_URL_SCHEME = 'https'

#: Secret keys
SECRET_KEYS = ['make this something random']
#: Lastuser secret keys (for the auth cookie)
LASTUSER_SECRET_KEYS = ['make this something random']


# ==== DOMAINS ====

#: Server name (required to generate URLs)
SERVER_NAME = 'funnel.test:3000'
#: Default domain (server name without port number)
DEFAULT_DOMAIN = 'funnel.test'
#: Shortlink domain for SMS links (must be served via wsgi:shortlinkapp)
SHORTLINK_DOMAIN = 'f.test'
#: Lastuser cookie domain
LASTUSER_COOKIE_DOMAIN = '.' + DEFAULT_DOMAIN
#: Unsubscribe token domain
UNSUBSCRIBE_DOMAIN = 'bye.li'


# ==== MAIL SETUP ====

#: Mail settings
#: MAIL_FAIL_SILENTLY : default True
#: MAIL_SERVER : default 'localhost'
#: MAIL_PORT : default 25
#: MAIL_USE_TLS : default False
#: MAIL_USE_SSL : default False
#: MAIL_USERNAME : default None
#: MAIL_PASSWORD : default None
#: DEFAULT_MAIL_SENDER : default None
MAIL_FAIL_SILENTLY = True
MAIL_SERVER = 'localhost'
MAIL_DEFAULT_SENDER = 'Sender <sender@domain.tld>'
#: Logging: recipients of error emails
ADMINS = []  # type: ignore[var-annotated]  # Remove this comment when editing


# ==== INTEGRATIONS ====

#: Internal
HASCORE_SERVER = ''
BOXOFFICE_SERVER = ''
HASJOB_SERVER = ''
IMGEE_HOST = ''
# IMAGE_URL_SCHEMES = {'https'}
# IMAGE_URL_DOMAINS = {'hasgeek.com', 'images.hasgeek.com', 'imgee.s3.amazonaws.com'}

#: TypeKit code for fonts
TYPEKIT_CODE = ''

#: Twitter integration
OAUTH_TWITTER_KEY = ''  # nosec
OAUTH_TWITTER_SECRET = ''  # nosec
OAUTH_TWITTER_ACCESS_KEY = ''  # nosec
OAUTH_TWITTER_ACCESS_SECRET = ''  # nosec

#: GitHub integration
OAUTH_GITHUB_KEY = ''  # nosec
OAUTH_GITHUB_SECRET = ''  # nosec

#: Google integration. Get an app here: https://console.developers.google.com/
OAUTH_GOOGLE_KEY = ''  # nosec
OAUTH_GOOGLE_SECRET = ''  # nosec
#: Default is ['email', 'profile']
OAUTH_GOOGLE_SCOPE = ['email', 'profile']  # nosec

#: LinkedIn integration
OAUTH_LINKEDIN_KEY = ''  # nosec
OAUTH_LINKEDIN_SECRET = ''  # nosec

#: Youtube integration
YOUTUBE_API_KEY = ''

#: Vimeo integration
VIMEO_CLIENT_ID = ''  # nosec
VIMEO_CLIENT_SECRET = ''  # nosec
VIMEO_ACCESS_TOKEN = ''  # nosec

#: Google Maps integration
GOOGLE_MAPS_API_KEY = ''

#: Recaptcha for the registration form
RECAPTCHA_USE_SSL = True  # nosec
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_OPTIONS = ''


# ==== NOTIFICATIONS ====

#: SMS gateways
#: Exotel support is active
SMS_EXOTEL_SID = ''  # nosec
SMS_EXOTEL_TOKEN = ''  # nosec
SMS_EXOTEL_FROM = ''  # nosec

#: DLT registered entity id and template ids
SMS_DLT_ENTITY_ID = ''  # nosec
SMS_DLT_TEMPLATE_IDS = {
    'web_otp_template': '',
    'one_line_template': '',
    'two_line_template': '',
}

#: Twilio support for non-indian numbers
SMS_TWILIO_SID = ''  # nosec
SMS_TWILIO_TOKEN = ''  # nosec
SMS_TWILIO_FROM = ''  # nosec

# SES Notification Topic
SES_NOTIFICATION_TOPICS = [
    # nosec
]
