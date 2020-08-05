from os import environ

TESTING = True
SECRET_KEYS = ['testkey']  # nosec
SITE_TITLE = 'Hasgeek'
SQLALCHEMY_DATABASE_URI = 'postgresql:///funnel_testing'
SERVER_NAME = 'funnel.travis.local:3002'
DEFAULT_DOMAIN = 'funnel.travis.local'
STATIC_SUBDOMAIN = 'static'
LASTUSER_COOKIE_DOMAIN = '.funnel.travis.local:3002'
LASTUSER_USE_SESSIONS = False
UPLOAD_FOLDER = '/tmp'  # nosec
TIMEZONE = 'Asia/Kolkata'
RQ_LOW_URL = 'redis://localhost:6379/0'
ASSET_BASE_PATH = "build"
HASCORE_SERVER = 'https://api.hasgeek.com'
GOOGLE_MAPS_API_KEY = environ.get('GOOGLE_MAPS_API_KEY')
BOXOFFICE_SERVER = 'https://boxoffice.hasgeek.com/api/1/'

ASSET_MANIFEST_PATH = "static/build/manifest.json"
ASSET_BASE_PATH = "build"
#: Recaptcha for the registration form
RECAPTCHA_USE_SSL = True
RECAPTCHA_PUBLIC_KEY = environ.get('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = environ.get('RECAPTCHA_PRIVATE_KEY')
RECAPTCHA_OPTIONS = ''
WTF_CSRF_ENABLED = False
WTF_CSRF_METHODS = {}

YOUTUBE_API_KEY = environ.get('YOUTUBE_API_KEY', '')

SITE_SUPPORT_EMAIL = environ.get('SITE_SUPPORT_EMAIL')
MAIL_SUPPRESS_SEND = True
MAIL_SERVER = environ.get('MAIL_SERVER')
MAIL_PORT = environ.get('MAIL_PORT')
MAIL_USE_SSL = environ.get('MAIL_USE_SSL')
MAIL_USE_TLS = environ.get('MAIL_USE_TLS')
MAIL_DEFAULT_SENDER = environ.get('MAIL_DEFAULT_SENDER', 'test@example.com')
MAIL_USERNAME = environ.get('MAIL_USERNAME')
MAIL_PASSWORD = environ.get('MAIL_PASSWORD')

#: Logging: recipients of error emails
ADMINS = environ.get('ADMINS')

#: Twitter integration
OAUTH_TWITTER_KEY = environ.get('OAUTH_TWITTER_KEY')
OAUTH_TWITTER_SECRET = environ.get('OAUTH_TWITTER_SECRET')

#: GitHub integration
OAUTH_GITHUB_KEY = environ.get('OAUTH_GITHUB_KEY')
OAUTH_GITHUB_SECRET = environ.get('OAUTH_GITHUB_KEY')

#: Google integration
OAUTH_GOOGLE_KEY = environ.get('OAUTH_GOOGLE_KEY')
OAUTH_GOOGLE_SECRET = environ.get('OAUTH_GOOGLE_SECRET')
#: Default is ['email', 'profile']
OAUTH_GOOGLE_SCOPE = ['email', 'profile']

#: Google Analytics code UA-XXXXXX-X
GA_CODE = environ.get('GA_CODE')

#: Recaptcha for the registration form
RECAPTCHA_USE_SSL = True
RECAPTCHA_PUBLIC_KEY = environ.get('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = environ.get('RECAPTCHA_PRIVATE_KEY')
RECAPTCHA_OPTIONS = ''

#: Exotel support is active
SMS_EXOTEL_SID = environ.get('SMS_EXOTEL_SID')
SMS_EXOTEL_TOKEN = environ.get('SMS_EXOTEL_TOKEN')
SMS_EXOTEL_FROM = environ.get('SMS_EXOTEL_FROM')

#: Twilio support for non-indian numbers
SMS_TWILIO_SID = environ.get('SMS_TWILIO_SID')
SMS_TWILIO_TOKEN = environ.get('SMS_TWILIO_TOKEN')
SMS_TWILIO_FROM = environ.get('SMS_TWILIO_FROM')

# nosec
