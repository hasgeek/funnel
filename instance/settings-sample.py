#: The title of this site
SITE_TITLE = 'Hasgeek Funnel'
#: Support contact email
SITE_SUPPORT_EMAIL = 'test@example.com'
#: Google Analytics code UA-XXXXXX-X
GA_CODE = ''
#: Server name (required to generate URLs)
SERVER_NAME = 'funnel.test:3000'
#: Database backend
SQLALCHEMY_DATABASE_URI = 'postgresql://host/database'
SQLALCHEMY_BINDS = {
    'geoname': 'postgresql://host/geoname',
}
#: Shortlink domain for SMS links (must be served via wsgi:shortlinkapp)
SHORTLINK_DOMAIN = 'domain.tld'
#: Secret keys
SECRET_KEYS = ['make this something random']
#: Timezone
TIMEZONE = 'Asia/Kolkata'
#: Lastuser secret keys (for the auth cookie)
LASTUSER_SECRET_KEYS = ['make this something random']
#: Lastuser cookie domain
LASTUSER_COOKIE_DOMAIN = '.mydomain.tld'
#: Used for attribution when shared a proposal on twitter
TWITTER_ID = "hasgeek"
#: Mail settings
#: MAIL_FAIL_SILENTLY : default True
#: MAIL_SERVER : default 'localhost'
#: MAIL_PORT : default 25
#: MAIL_USE_TLS : default False
#: MAIL_USE_SSL : default False
#: MAIL_USERNAME : default None
#: MAIL_PASSWORD : default None
#: DEFAULT_MAIL_SENDER : default None
MAIL_FAIL_SILENTLY = False
MAIL_SERVER = 'localhost'
DEFAULT_MAIL_SENDER = ('Bill Gate', 'test@example.com')

# Required for Flask-Mail to work.
MAIL_DEFAULT_SENDER = DEFAULT_MAIL_SENDER
#: Logging: recipients of error emails
ADMINS = []  # type: ignore[var-annotated]  # Remove this comment when editing
#: Log file
LOGFILE = 'error.log'

CACHE_TYPE = 'redis'
RQ_REDIS_URL = 'redis://localhost:6379/0'
RQ_SCHEDULER_INTERVAL = 1
DEBUG = True

#: Twitter integration
OAUTH_TWITTER_KEY = ''  # nosec
OAUTH_TWITTER_SECRET = ''  # nosec

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

#: Recaptcha for the registration form
RECAPTCHA_USE_SSL = True  # nosec
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_OPTIONS = ''

#: SMS gateways
#: SMSGupShup support is deprecated
SMS_SMSGUPSHUP_MASK = ''
SMS_SMSGUPSHUP_USER = ''  # nosec
SMS_SMSGUPSHUP_PASS = ''  # nosec
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

#: Unsubscribe token domain
UNSUBSCRIBE_DOMAIN = 'bye.li'

IMGEE_HOST = ''
