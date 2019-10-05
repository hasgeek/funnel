#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

from flask import Flask
from flask_flatpages import FlatPages
from flask_mail import Mail
from flask_migrate import Migrate
from flask_rq2 import RQ

from flask_lastuser import Lastuser
from flask_lastuser.sqlalchemy import UserManager

from baseframe import Bundle, Version, assets, baseframe
import coaster.app

from ._version import __version__

app = Flask(__name__, instance_relative_config=True)
funnelapp = Flask(__name__, instance_relative_config=True, subdomain_matching=True)
mail = Mail()
lastuser = Lastuser()
pages = FlatPages()
rq = RQ()


# --- Assets ------------------------------------------------------------------

version = Version(__version__)
assets['funnel.css'][version] = 'css/app.css'
assets['funnel.js'][version] = 'js/scripts.js'
assets['spectrum.js'][version] = 'js/libs/spectrum.js'
assets['spectrum.css'][version] = 'css/spectrum.css'
assets['screens.css'][version] = 'css/screens.css'
assets['schedules.js'][version] = 'js/schedules.js'
assets['schedule-print.css'][version] = 'css/schedule-print.css'

# --- Import rest of the app --------------------------------------------------

from . import models, forms, views  # NOQA  # isort:skip
from .models import db  # isort:skip


# --- Configuration------------------------------------------------------------
coaster.app.init_app(app)
coaster.app.init_app(funnelapp)

# These are app specific confguration files that must exist
# inside the `instance/` directory. Sample config files are
# provided as example.
coaster.app.load_config_from_file(app, 'hasgeekapp.py')
coaster.app.load_config_from_file(funnelapp, 'funnelapp.py')

app.config['LEGACY'] = False
funnelapp.config['LEGACY'] = True

db.init_app(app)
db.init_app(funnelapp)

migrate = Migrate(app, db)

mail.init_app(app)
mail.init_app(funnelapp)

lastuser.init_app(app)
lastuser.init_app(funnelapp)

lastuser.init_usermanager(UserManager(db, models.User, models.Team))
app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['markdown.extensions.nl2br']
pages.init_app(app)

rq.init_app(app)
rq.init_app(funnelapp)

baseframe.init_app(
    app,
    requires=['funnel'],
    ext_requires=['pygments', 'toastr', 'baseframe-mui'],
    theme='mui',
)
baseframe.init_app(
    funnelapp,
    requires=['funnel'],
    ext_requires=['pygments', 'toastr', 'baseframe-mui'],
    theme='mui',
)

# Register JS and CSS assets on both apps
app.assets.register(
    'js_fullcalendar',
    Bundle(
        assets.require(
            '!jquery.js',
            'jquery.fullcalendar.js',
            'moment.js',
            'moment-timezone-data.js',
            'spectrum.js',
            'jquery.ui.sortable.touch.js',
        ),
        output='js/fullcalendar.packed.js',
        filters='uglipyjs',
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
        filters='uglipyjs',
    ),
)
app.assets.register(
    'js_codemirrormarkdown',
    Bundle(
        assets.require('codemirror-markdown.js'),
        output='js/codemirror-markdown.packed.js',
        filters='uglipyjs',
    ),
)
app.assets.register(
    'css_codemirrormarkdown',
    Bundle(
        assets.require('codemirror-markdown.css'),
        output='css/codemirror-markdown.packed.css',
        filters='cssmin',
    ),
)
app.assets.register(
    'css_screens',
    Bundle(
        assets.require('screens.css'),
        output='css/screens.packed.css',
        filters='cssmin'
    ),
)
app.assets.register(
    'js_jquerysuccinct',
    Bundle(
        assets.require('!jquery.js', 'jquery.succinct.js'),
        output='js/jquerysuccinct.packed.js',
        filters='uglipyjs',
    ),
)
app.assets.register(
    'js_jqueryeasytabs',
    Bundle(
        assets.require('!jquery.js', 'jquery-easytabs.js'),
        output='js/jqueryeasytabs.packed.js',
        filters='uglipyjs',
    ),
)
app.assets.register(
    'js_leaflet',
    Bundle(
        assets.require('leaflet.js', 'leaflet-search.js'),
        output='js/leaflet.packed.js',
        filters='uglipyjs',
    ),
)
app.assets.register(
    'css_leaflet',
    Bundle(
        assets.require('leaflet.css', 'leaflet-search.css'),
        output='css/leaflet.packed.css',
        filters='cssmin',
    ),
)
app.assets.register(
    'js_emojionearea',
    Bundle(
        assets.require('!jquery.js', 'emojionearea-material.js'),
        output='js/emojionearea.packed.js',
        filters='uglipyjs',
    ),
)
app.assets.register(
    'css_emojionearea',
    Bundle(
        assets.require('emojionearea-material.css'),
        output='css/emojionearea.packed.css',
        filters='cssmin',
    ),
)
app.assets.register(
    'js_sortable',
    Bundle(
        assets.require('!jquery.js', 'jquery.ui.js', 'jquery.ui.sortable.touch.js'),
        output='js/sortable.packed.js',
        filters='uglipyjs',
    ),
)
app.assets.register(
    'css_schedule_print',
    Bundle(
        assets.require('schedule-print.css'),
        output='css/schedule-print.packed.css',
        filters='cssmin'
    ),
)

funnelapp.assets.register(
    'js_fullcalendar',
    Bundle(
        assets.require(
            '!jquery.js',
            'jquery.fullcalendar.js',
            'moment.js',
            'moment-timezone-data.js',
            'spectrum.js',
            'jquery.ui.sortable.touch.js',
        ),
        output='js/fullcalendar.packed.js',
        filters='uglipyjs',
    ),
)
funnelapp.assets.register(
    'css_fullcalendar',
    Bundle(
        assets.require('jquery.fullcalendar.css', 'spectrum.css'),
        output='css/fullcalendar.packed.css',
        filters='cssmin',
    ),
)
funnelapp.assets.register(
    'js_schedules',
    Bundle(
        assets.require('schedules.js'),
        output='js/schedules.packed.js',
        filters='uglipyjs',
    ),
)
funnelapp.assets.register(
    'js_codemirrormarkdown',
    Bundle(
        assets.require('codemirror-markdown.js'),
        output='js/codemirror-markdown.packed.js',
        filters='uglipyjs',
    ),
)
funnelapp.assets.register(
    'css_codemirrormarkdown',
    Bundle(
        assets.require('codemirror-markdown.css'),
        output='css/codemirror-markdown.packed.css',
        filters='cssmin',
    ),
)
funnelapp.assets.register(
    'css_screens',
    Bundle(
        assets.require('screens.css'), output='css/screens.packed.css', filters='cssmin'
    ),
)
funnelapp.assets.register(
    'js_jquerysuccinct',
    Bundle(
        assets.require('!jquery.js', 'jquery.succinct.js'),
        output='js/jquerysuccinct.packed.js',
        filters='uglipyjs',
    ),
)
funnelapp.assets.register(
    'js_jqueryeasytabs',
    Bundle(
        assets.require('!jquery.js', 'jquery-easytabs.js'),
        output='js/jqueryeasytabs.packed.js',
        filters='uglipyjs',
    ),
)
funnelapp.assets.register(
    'js_leaflet',
    Bundle(
        assets.require('leaflet.js', 'leaflet-search.js'),
        output='js/leaflet.packed.js',
        filters='uglipyjs',
    ),
)
funnelapp.assets.register(
    'css_leaflet',
    Bundle(
        assets.require('leaflet.css', 'leaflet-search.css'),
        output='css/leaflet.packed.css',
        filters='cssmin',
    ),
)
funnelapp.assets.register(
    'js_emojionearea',
    Bundle(
        assets.require('!jquery.js', 'emojionearea-material.js'),
        output='js/emojionearea.packed.js',
        filters='uglipyjs',
    ),
)
funnelapp.assets.register(
    'css_emojionearea',
    Bundle(
        assets.require('emojionearea-material.css'),
        output='css/emojionearea.packed.css',
        filters='cssmin',
    ),
)
funnelapp.assets.register(
    'js_sortable',
    Bundle(
        assets.require('!jquery.js', 'jquery.ui.js', 'jquery.ui.sortable.touch.js'),
        output='js/sortable.packed.js',
        filters='uglipyjs',
    ),
)
funnelapp.assets.register(
    'css_schedule_print',
    Bundle(
        assets.require('schedule-print.css'),
        output='css/schedule-print.packed.css',
        filters='cssmin'
    ),
)


# FIXME: Hack for external build system generating relative /static URLs.
# Fix this by generating absolute URLs to the static subdomain during build.
funnelapp.add_url_rule(
    '/static/<path:filename>',
    endpoint='static',
    view_func=funnelapp.send_static_file,
    subdomain=None,
)
funnelapp.add_url_rule(
    '/static/<path:filename>',
    endpoint='static',
    view_func=funnelapp.send_static_file,
    subdomain='<subdomain>',
)

# Database model loading (from Funnel or extensions) is complete.
# Configure database mappers now, before the process is forked for workers.
db.configure_mappers()
