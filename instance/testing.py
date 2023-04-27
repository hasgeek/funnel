"""Test configuration."""

from os import environ

TESTING = True
DEBUG_TB_ENABLED = False
CACHE_TYPE = 'RedisCache'
SECRET_KEYS = ['testkey']  # nosec
LASTUSER_SECRET_KEYS = ['testkey']  # nosec
SITE_TITLE = 'Hasgeek'
SQLALCHEMY_DATABASE_URI = (
    f'postgresql://{environ.get("POSTGRES_USER_HOST", "localhost")}:5432/funnel_testing'
)
SQLALCHEMY_BINDS = {
    'geoname': f'postgresql://{environ.get("POSTGRES_USER_HOST", "localhost")}:5432/geoname_testing',
}
SERVER_NAME = 'funnel.test:3002'
SHORTLINK_DOMAIN = 'f.test:3002'
DEFAULT_DOMAIN = 'funnel.test'
STATIC_SUBDOMAIN = 'static'
LASTUSER_COOKIE_DOMAIN = '.funnel.test:3002'
UPLOAD_FOLDER = '/tmp'  # nosec
TIMEZONE = 'Asia/Kolkata'
GOOGLE_MAPS_API_KEY = environ.get('GOOGLE_MAPS_API_KEY')
BOXOFFICE_SERVER = 'https://boxoffice.hasgeek.com/api/1/'
# Run RQ jobs inline in tests
RQ_ASYNC = False
# Use Redis db 9 for tests
REDIS_URL = (
    RQ_REDIS_URL
) = CACHE_REDIS_URL = f'redis://{environ.get("REDIS_HOST", "localhost")}:6379/9'

UNSUBSCRIBE_DOMAIN = 'bye.test'
#: Recaptcha for the registration form
RECAPTCHA_USE_SSL = True
# Recaptcha keys from https://developers.google.com/recaptcha/docs/faq
# #id-like-to-run-automated-tests-with-recaptcha.-what-should-i-do
RECAPTCHA_PUBLIC_KEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'
RECAPTCHA_PRIVATE_KEY = '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe'
RECAPTCHA_OPTIONS = ''
WTF_CSRF_ENABLED = True

YOUTUBE_API_KEY = environ.get('YOUTUBE_API_KEY', '')

SITE_SUPPORT_EMAIL = environ.get('SITE_SUPPORT_EMAIL')
SITE_SUPPORT_PHONE = environ.get('SITE_SUPPORT_PHONE')
MAIL_SUPPRESS_SEND = True
MAIL_SERVER = environ.get('MAIL_SERVER')
MAIL_PORT = int(environ.get('MAIL_PORT', 25))
MAIL_USE_SSL = bool(environ.get('MAIL_USE_SSL', False))
MAIL_USE_TLS = bool(environ.get('MAIL_USE_TLS', False))
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

#: Exotel support is active
SMS_EXOTEL_SID = environ.get('SMS_EXOTEL_SID')
SMS_EXOTEL_TOKEN = environ.get('SMS_EXOTEL_TOKEN')
SMS_EXOTEL_FROM = environ.get('SMS_EXOTEL_FROM')
SMS_DLT_ENTITY_ID = environ.get('SMS_DLT_ENTITY_ID')

#: Twilio support for non-indian numbers
# SMS_TWILIO_SID = environ.get('SMS_TWILIO_SID')
# SMS_TWILIO_TOKEN = environ.get('SMS_TWILIO_TOKEN')
# SMS_TWILIO_FROM = environ.get('SMS_TWILIO_FROM')

#: Vimeo API key
VIMEO_CLIENT_ID = environ.get('VIMEO_CLIENT_ID')
VIMEO_CLIENT_SECRET = environ.get('VIMEO_CLIENT_SECRET')
VIMEO_ACCESS_TOKEN = environ.get('VIMEO_ACCESS_TOKEN')

#: SES notification topics
SES_NOTIFICATION_TOPICS = [  # nosec
    'arn:aws:sns:ap-south-1:817922165072:ses-events-for-hasgeek_dot_com'
]

IMGEE_HOST = 'https://images.example.com'
IMAGE_URL_DOMAINS = ('images.example.com',)
IMAGE_URL_SCHEMES = ('https',)

ENABLE_COMMENT_SIDEBAR = True
