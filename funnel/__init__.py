"""Hasgeek website app bootstrap."""

from __future__ import annotations

import logging
from datetime import timedelta
from email.utils import parseaddr

import phonenumbers
from flask import Flask
from flask_babel import get_locale
from flask_executor import Executor
from flask_flatpages import FlatPages
from flask_mailman import Mail
from flask_migrate import Migrate
from flask_redis import FlaskRedis
from flask_rq2 import RQ
from whitenoise import WhiteNoise

import coaster.app
from baseframe import Bundle, Version, __, assets, baseframe
from baseframe.blueprint import THEME_FILES
from coaster.assets import WebpackManifest

from ._version import __version__

#: Main app for hasgeek.com
app = Flask(__name__, instance_relative_config=True)
app.name = 'funnel'
app.config['SITE_TITLE'] = __("Hasgeek")
#: Shortlink app at has.gy
shortlinkapp = Flask(__name__, static_folder=None, instance_relative_config=True)
shortlinkapp.name = 'shortlink'
#: Unsubscribe app at bye.li
unsubscribeapp = Flask(__name__, static_folder=None, instance_relative_config=True)
unsubscribeapp.name = 'unsubscribe'

all_apps = [app, shortlinkapp, unsubscribeapp]

mail = Mail()
pages = FlatPages()
manifest = WebpackManifest(filepath='static/build/manifest.json')

redis_store = FlaskRedis(decode_responses=True, config_prefix='CACHE_REDIS')
rq = RQ()
rq.job_class = 'rq.job.Job'
rq.queues = ['funnel']  # Queues used in this app
executor = Executor()

# --- Assets ---------------------------------------------------------------------------

#: Theme files, for transitioning away from Baseframe templates. These are used by
#: Baseframe's render_form and other form helper functions.
THEME_FILES['funnel'] = {
    'ajaxform.html.jinja2': 'ajaxform.html.jinja2',
    'autoform.html.jinja2': 'autoform.html.jinja2',
    'delete.html.jinja2': 'delete.html.jinja2',
    'message.html.jinja2': 'message.html.jinja2',
    'redirect.html.jinja2': 'redirect.html.jinja2',
}

version = Version(__version__)
assets['funnel.js'][version] = 'js/scripts.js'
assets['spectrum.js'][version] = 'js/libs/spectrum.js'
assets['spectrum.css'][version] = 'css/spectrum.css'
assets['schedules.js'][version] = 'js/schedules.js'


# --- Import rest of the app -----------------------------------------------------------

from . import (  # isort:skip  # noqa: F401  # pylint: disable=wrong-import-position
    geoip,
    proxies,
    loginproviders,
    signals,
    models,
    transports,
    forms,
    views,
    cli,
)
from .models import db, sa  # isort:skip  # pylint: disable=wrong-import-position

# --- Configuration---------------------------------------------------------------------

# Config is loaded from legacy Python settings files in the instance folder and then
# overridden with values from the environment. Python config is pending deprecation
# All supported config values are listed in ``sample.env``. If an ``.env`` file is
# present, it is loaded in debug and testing modes only
for each_app in all_apps:
    coaster.app.init_app(
        each_app, ['py', 'env'], env_prefix=['FLASK', f'APP_{each_app.name.upper()}']
    )

# Legacy additional config for the main app (pending deprecation)
coaster.app.load_config_from_file(app, 'hasgeekapp.py')

# Force specific config settings, overriding deployment config
shortlinkapp.config['SERVER_NAME'] = app.config['SHORTLINK_DOMAIN']
if app.config.get('UNSUBSCRIBE_DOMAIN'):
    unsubscribeapp.config['SERVER_NAME'] = app.config['UNSUBSCRIBE_DOMAIN']
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
app.config['SESSION_REFRESH_EACH_REQUEST'] = False
app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['markdown.extensions.nl2br']
app.config['FLATPAGES_EXTENSION'] = '.md'
app.config['EXECUTOR_PROPAGATE_EXCEPTIONS'] = True
app.config['EXECUTOR_PUSH_APP_CONTEXT'] = True
# Remove legacy asset manifest settings that Baseframe looks for
app.config.pop('ASSET_MANIFEST_PATH', None)
app.config.pop('ASSET_BASE_PATH', None)

# Install common extensions on all apps
for each_app in all_apps:
    # If MAIL_DEFAULT_SENDER is in the form "Name <email>", extract email
    each_app.config['MAIL_DEFAULT_SENDER_ADDR'] = parseaddr(
        app.config['MAIL_DEFAULT_SENDER']
    )[1]
    each_app.config['SITE_SUPPORT_PHONE_FORMATTED'] = phonenumbers.format_number(
        phonenumbers.parse(each_app.config['SITE_SUPPORT_PHONE']),
        phonenumbers.PhoneNumberFormat.INTERNATIONAL,
    )
    proxies.init_app(each_app)
    manifest.init_app(each_app)
    db.init_app(each_app)
    mail.init_app(each_app)

    # Downgrade logging from default WARNING level to INFO unless in debug mode
    if not each_app.debug:
        each_app.logger.setLevel(logging.INFO)

# TODO: Move this into Baseframe
app.jinja_env.globals['get_locale'] = get_locale

# TODO: Replace this with something cleaner. The `login_manager` attr expectation is
# from coaster.auth. It attempts to call `current_app.login_manager._load_user`, an
# API it borrows from the Flask-Login extension
app.login_manager = views.login_session.LoginManager()  # type: ignore[attr-defined]

# These extensions are only required in the main app
migrate = Migrate(app, db)
pages.init_app(app)
redis_store.init_app(app)
rq.init_app(app)
executor.init_app(app)
geoip.geoip.init_app(app)

# Baseframe is required for apps with UI ('funnel' theme is registered above)
baseframe.init_app(app, requires=['funnel'], theme='funnel', error_handlers=False)

# Initialize available login providers from app config
loginproviders.init_app(app)

# Ensure FEATURED_ACCOUNTS is a list, not None
if not app.config.get('FEATURED_ACCOUNTS'):
    app.config['FEATURED_ACCOUNTS'] = []

# Turn on supported notification transports
transports.init()

# Register JS and CSS assets on both apps
app.assets.register(  # type: ignore[attr-defined]
    'js_fullcalendar',
    Bundle(
        assets.require(
            '!jquery.js',
            'jquery.fullcalendar.js',
            'moment.js',
            'moment-timezone-data.js',
            'spectrum.js',
            'toastr.js',
            'jquery.ui.sortable.touch.js',
        ),
        output='js/fullcalendar.packed.js',
        filters='rjsmin',
    ),
)
app.assets.register(
    'css_fullcalendar',
    Bundle(
        assets.require('jquery.fullcalendar.css', 'spectrum.css'),
        output='css/fullcalendar.packed.css',
        filters='cssmin',
    ),
)
app.assets.register(
    'js_schedules',
    Bundle(
        assets.require('schedules.js'),
        output='js/schedules.packed.js',
        filters='rjsmin',
    ),
)

views.siteadmin.init_rq_dashboard()

# --- Serve static files with Whitenoise -----------------------------------------------

app.wsgi_app = WhiteNoise(  # type: ignore[method-assign]
    app.wsgi_app, root=app.static_folder, prefix=app.static_url_path
)
app.wsgi_app.add_files(  # type: ignore[attr-defined]
    baseframe.static_folder, prefix=baseframe.static_url_path
)

# --- Init SQLAlchemy mappers ----------------------------------------------------------

# Database model loading (from Funnel or extensions) is complete.
# Configure database mappers now, before the process is forked for workers.
sa.orm.configure_mappers()
