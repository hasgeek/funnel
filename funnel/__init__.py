"""Hasgeek website app bootstrap."""

from __future__ import annotations

from datetime import timedelta
import logging
import os.path

from flask import Flask
from flask_babel import get_locale
from flask_executor import Executor
from flask_flatpages import FlatPages
from flask_mailman import Mail
from flask_migrate import Migrate
from flask_redis import FlaskRedis
from flask_rq2 import RQ
from whitenoise import WhiteNoise
import geoip2.database

from baseframe import Bundle, Version, assets, baseframe
from baseframe.blueprint import THEME_FILES
from coaster.assets import WebpackManifest
import coaster.app

from ._version import __version__

#: Main app for hasgeek.com
app = Flask(__name__, instance_relative_config=True)
#: Shortlink app at has.gy
shortlinkapp = Flask(__name__, static_folder=None, instance_relative_config=True)
#: Unsubscribe app at bye.li
unsubscribeapp = Flask(__name__, static_folder=None, instance_relative_config=True)

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
    models,
    signals,
    forms,
    loginproviders,
    transports,
    views,
    cli,
    proxies,
)
from .models import db, sa  # isort:skip  # pylint: disable=wrong-import-position

# --- Configuration---------------------------------------------------------------------

# Config is loaded from legacy Python settings files in the instance folder and then
# overridden with values from the environment. Python config is pending deprecation
# All supported config values are listed in ``sample.env``. If an ``.env`` file is
# present, it is loaded in debug and testing modes only
coaster.app.init_app(app, ['py', 'env'], env_prefix=['FLASK', 'APP_FUNNEL'])
coaster.app.init_app(
    shortlinkapp,
    ['py', 'env'],
    env_prefix=['FLASK', 'APP_SHORTLINK'],
    init_logging=False,
)
coaster.app.init_app(
    unsubscribeapp,
    ['py', 'env'],
    env_prefix=['FLASK', 'APP_UNSUBSCRIBE'],
    init_logging=False,
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
baseframe.init_app(app, requires=['funnel'], theme='funnel', error_handlers=False)

loginproviders.init_app(app)

# Load GeoIP2 databases
app.geoip_city = None
app.geoip_asn = None
if 'GEOIP_DB_CITY' in app.config:
    if not os.path.exists(app.config['GEOIP_DB_CITY']):
        app.logger.warning(
            "GeoIP city database missing at %s", app.config['GEOIP_DB_CITY']
        )
    else:
        app.geoip_city = geoip2.database.Reader(app.config['GEOIP_DB_CITY'])

if 'GEOIP_DB_ASN' in app.config:
    if not os.path.exists(app.config['GEOIP_DB_ASN']):
        app.logger.warning(
            "GeoIP ASN database missing at %s", app.config['GEOIP_DB_ASN']
        )
    else:
        app.geoip_asn = geoip2.database.Reader(app.config['GEOIP_DB_ASN'])

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
