#!/bin/bash
set -e
# A copy of these settings is in pyproject.toml:tool.pytest.ini_options:env
export FLASK_ENV=testing
export FLASK_TESTING=true
export FLASK_DEBUG_TB_ENABLED=false
# Enable CSRF so tests reflect production use
export FLASK_WTF_CSRF_ENABLED=true
# Use Redis cache so that rate limit validation tests work, with Redis db
export FLASK_CACHE_TYPE=flask_caching.backends.RedisCache
export FLASK_REDIS_URL=redis://localhost:6379/9
export FLASK_RQ_REDIS_URL=redis://localhost:6379/9
export FLASK_RQ_DASHBOARD_REDIS_URL=redis://localhost:6379/9
export FLASK_CACHE_REDIS_URL=redis://localhost:6379/9
# Disable logging in tests
export FLASK_SQLALCHEMY_ECHO=false
export FLASK_ADMINS='[]'
export FLASK_TELEGRAM_ERROR_CHATID=null
export FLASK_TELEGRAM_ERROR_APIKEY=null
export SLACK_LOGGING_WEBHOOKS='[]'
# Run RQ jobs inline in tests
export FLASK_RQ_ASYNC=false
# Recaptcha keys from https://developers.google.com/recaptcha/docfaq#id-like-to-run-automated-tests-with-recaptcha.-what-should-i-do
export FLASK_RECAPTCHA_USE_SSL=true
export FLASK_RECAPTCHA_PUBLIC_KEY=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
export FLASK_RECAPTCHA_PRIVATE_KEY=6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe
export FLASK_RECAPTCHA_OPTIONS=""
# Use hostaliases on supported platforms
export HOSTALIASES=${PWD}/HOSTALIASES
# These settings should be customisable from a .env file (TODO)
export FLASK_SECRET_KEYS='["testkey"]'
export FLASK_LASTUSER_SECRET_KEYS='["testkey"]'
export FLASK_LASTUSER_COOKIE_DOMAIN='.funnel.test:3002'
export FLASK_SITE_TITLE='Test Hasgeek'
export FLASK_SITE_SUPPORT_EMAIL=test-support-email
export FLASK_SITE_SUPPORT_PHONE=test-support-phone
export FLASK_SQLALCHEMY_DATABASE_URI='postgresql+psycopg://localhost/funnel_testing'
export FLASK_SQLALCHEMY_BINDS__geoname='postgresql+psycopg://localhost/geoname_testing'
export FLASK_TIMEZONE='Asia/Kolkata'
export FLASK_BOXOFFICE_SERVER='http://boxoffice:6500/api/1/'
export FLASK_IMGEE_HOST='http://imgee.test:4500'
export FLASK_IMAGE_URL_DOMAINS='["images.example.com"]'
export FLASK_IMAGE_URL_SCHEMES='["https"]'
export FLASK_SES_NOTIFICATION_TOPIC=["arn:aws:sns:ap-south-1:817922165072:ses-events-for-hasgeek_dot_com"]
# Per app config
export APP_FUNNEL_SITE_ID=hasgeek-test
export APP_FUNNEL_SERVER_NAME=funnel.test:3002
export APP_FUNNEL_SHORTLINK_DOMAIN=f.test:3002
export APP_FUNNEL_DEFAULT_DOMAIN=funnel.test
export APP_FUNNEL_UNSUBSCRIBE_DOMAIN=bye.test
export APP_SHORTLINK_SITE_ID=shortlink-test

python -m tests.cypress.cypress_initdb_test
flask run -p 3002 --no-reload --debugger 2>&1 1>/tmp/funnel-server.log & echo $! > /tmp/funnel-server.pid
function killserver() {
    kill $(cat /tmp/funnel-server.pid)
    python -m tests.cypress.cypress_dropdb_test
    rm /tmp/funnel-server.pid
}
trap killserver INT
npx --prefix tests/cypress cypress run --browser chrome
killserver
