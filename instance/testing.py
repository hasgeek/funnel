# -*- coding: utf-8 -*-
import os

SECRET_KEY = 'testkey'
SITE_TITLE = 'HasGeek'
SQLALCHEMY_DATABASE_URI = 'postgresql:///funnel_testing'
SERVER_NAME = 'funnel.travis.local:3002'
STATIC_SUBDOMAIN = 'static'
LASTUSER_SERVER = 'https://auth.hasgeek.com/'
LASTUSER_CLIENT_ID = os.environ.get('LASTUSER_CLIENT_ID')
LASTUSER_CLIENT_SECRET = os.environ.get('LASTUSER_CLIENT_SECRET')
LASTUSER_COOKIE_DOMAIN = '.funnel.travis.local'
UPLOAD_FOLDER = '/tmp'
TIMEZONE = 'Asia/Kolkata'
RQ_LOW_URL = 'redis://localhost:6379/0'
ASSET_BASE_PATH = "build"
HASCORE_SERVER = 'https://api.hasgeek.com'

ASSET_MANIFEST_PATH = "static/build/manifest.json"
ASSET_BASE_PATH = "build"
#: Recaptcha for the registration form
RECAPTCHA_USE_SSL = True
RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_PRIVATE_KEY')
RECAPTCHA_OPTIONS = ''
WTF_CSRF_ENABLED = False
WTF_CSRF_METHODS = {}
