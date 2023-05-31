"""Test configuration."""

SECRET_KEYS = ['testkey']  # nosec
LASTUSER_SECRET_KEYS = ['testkey']  # nosec
SITE_TITLE = 'Hasgeek'
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg://localhost/funnel_testing'
SQLALCHEMY_BINDS = {
    'geoname': 'postgresql+psycopg://localhost/geoname_testing',
}
SERVER_NAME = 'funnel.test:3002'
SHORTLINK_DOMAIN = 'f.test:3002'
DEFAULT_DOMAIN = 'funnel.test'
LASTUSER_COOKIE_DOMAIN = '.funnel.test:3002'
TIMEZONE = 'Asia/Kolkata'
BOXOFFICE_SERVER = 'https://boxoffice.hasgeek.com/api/1/'

UNSUBSCRIBE_DOMAIN = 'bye.test'

#: SES notification topics
SES_NOTIFICATION_TOPICS = [  # nosec
    'arn:aws:sns:ap-south-1:817922165072:ses-events-for-hasgeek_dot_com'
]

IMGEE_HOST = 'https://images.example.com'
IMAGE_URL_DOMAINS = ('images.example.com',)
IMAGE_URL_SCHEMES = ('https',)

SITE_SUPPORT_EMAIL = 'test-support-email'
SITE_SUPPORT_PHONE = 'test-support-phone'
