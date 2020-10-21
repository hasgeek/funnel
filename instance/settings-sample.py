#: The title of this site
SITE_TITLE = 'Hasgeek Funnel'
#: Support contact email
SITE_SUPPORT_EMAIL = 'test@example.com'
#: TypeKit code for fonts
TYPEKIT_CODE = ''
#: Google Analytics code UA-XXXXXX-X
GA_CODE = ''
#: Database backend
SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
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

HASCORE_SERVER = 'https://api.hasgeek.com/'
CACHE_TYPE = 'redis'
RQ_REDIS_URL = 'redis://localhost:6379/0'
RQ_SCHEDULER_INTERVAL = 1
DEBUG = True
SMS_VERIFICATION_TEMPLATE = "Hello from Hasgeek. Your verification code is {code}."

#: Twitter integration
OAUTH_TWITTER_KEY = ''
OAUTH_TWITTER_SECRET = ''

#: GitHub integration
OAUTH_GITHUB_KEY = ''
OAUTH_GITHUB_SECRET = ''

#: Google integration. Get an app here: https://console.developers.google.com/
OAUTH_GOOGLE_KEY = ''
OAUTH_GOOGLE_SECRET = ''
#: Default is ['email', 'profile']
OAUTH_GOOGLE_SCOPE = ['email', 'profile']

#: LinkedIn integration
OAUTH_LINKEDIN_KEY = ''
OAUTH_LINKEDIN_SECRET = ''

#: Recaptcha for the registration form
RECAPTCHA_USE_SSL = True
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_OPTIONS = ''

#: SMS gateways
#: SMSGupShup support is deprecated
SMS_SMSGUPSHUP_MASK = ''
SMS_SMSGUPSHUP_USER = ''
SMS_SMSGUPSHUP_PASS = ''
#: Exotel support is active
SMS_EXOTEL_SID = ''
SMS_EXOTEL_TOKEN = ''
SMS_EXOTEL_FROM = ''
#: Twilio support for non-indian numbers
SMS_TWILIO_SID = ''
SMS_TWILIO_TOKEN = ''
SMS_TWILIO_FROM = ''

#: Unsubscribe token domain
UNSUBSCRIBE_DOMAIN = 'bye.li'
