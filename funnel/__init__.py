#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import coaster.app
from flask import Flask
from flask_flatpages import FlatPages
from flask_migrate import Migrate
from flask_mail import Mail
from flask_lastuser import Lastuser
from flask_lastuser.sqlalchemy import UserManager
from baseframe import baseframe, assets, Version, Bundle
from ._version import __version__


app = Flask(__name__, instance_relative_config=True, subdomain_matching=True)
mail = Mail()
lastuser = Lastuser()
pages = FlatPages()


# --- Assets ------------------------------------------------------------------

version = Version(__version__)
assets['funnel.js'][version] = 'js/scripts.js'
assets['funnel.css'][version] = 'css/app.css'
assets['spectrum.js'][version] = 'js/libs/spectrum.js'
assets['spectrum.css'][version] = 'css/spectrum.css'
assets['schedules.css'][version] = 'css/schedules.css'
assets['schedules.js'][version] = 'js/schedules.js'
assets['screens.css'][version] = 'css/screens.css'


# --- Import rest of the app --------------------------------------------------

from . import models, forms, views  # NOQA
from .models import db


# --- Configuration------------------------------------------------------------
coaster.app.init_app(app)
db.init_app(app)
db.app = app
migrate = Migrate(app, db)
mail.init_app(app)
lastuser.init_app(app)
lastuser.init_usermanager(UserManager(db, models.User, models.Team))
pages.init_app(app)
baseframe.init_app(app, requires=['funnel'], ext_requires=[
    ('codemirror-markdown', 'pygments'), 'toastr', 'baseframe-mui', 'fontawesome>=4.0.0',
    'ractive', 'jquery-easytabs'], theme='mui')
app.assets.register('js_fullcalendar',
    Bundle(assets.require('!jquery.js', 'jquery.fullcalendar.js', 'spectrum.js'),
        output='js/fullcalendar.packed.js', filters='uglipyjs'))
app.assets.register('css_fullcalendar',
    Bundle(assets.require('jquery.fullcalendar.css', 'spectrum.css', 'schedules.css'),
        output='css/fullcalendar.packed.css', filters='cssmin'))
app.assets.register('js_schedules',
    Bundle(assets.require('schedules.js'),
        output='js/schedules.packed.js', filters='uglipyjs'))
app.assets.register('css_screens',
    Bundle(assets.require('screens.css'),
        output='css/screens.packed.css', filters='cssmin'))

# FIXME: Hack for external build system generating relative /static URLs.
# Fix this by generating absolute URLs to the static subdomain during build.
app.add_url_rule('/static/<path:filename>', endpoint='static',
    view_func=app.send_static_file, subdomain=None)
app.add_url_rule('/static/<path:filename>', endpoint='static',
    view_func=app.send_static_file, subdomain='<subdomain>')
