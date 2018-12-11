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
from flask_rq2 import RQ
from baseframe import baseframe, assets, Version, Bundle
from ._version import __version__


app = Flask(__name__, instance_relative_config=True)
funnelapp = Flask(__name__, instance_relative_config=True, subdomain_matching=True)
mail = Mail()
lastuser = Lastuser()
pages = FlatPages()
rq = RQ()


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
pages.init_app(app)

rq.init_app(app)
rq.init_app(funnelapp)

baseframe.init_app(app, requires=['funnel'], ext_requires=[
    'pygments', 'toastr', 'baseframe-mui', 'fontawesome>=4.0.0',
    'jquery-easytabs'], theme='mui')
app.assets.register('js_fullcalendar',
    Bundle(assets.require('!jquery.js', 'jquery.fullcalendar.js', 'spectrum.js'),
        output='js/fullcalendar.packed.js', filters='uglipyjs'))
app.assets.register('css_fullcalendar',
    Bundle(assets.require('jquery.fullcalendar.css', 'spectrum.css', 'schedules.css'),
        output='css/fullcalendar.packed.css', filters='cssmin'))
app.assets.register('js_schedules',
    Bundle(assets.require('schedules.js'),
        output='js/schedules.packed.js', filters='uglipyjs'))
app.assets.register('js_codemirrormarkdown',
    Bundle(assets.require('codemirror-markdown.js'),
        output='js/codemirror-markdown.packed.js', filters='uglipyjs'))
app.assets.register('css_codemirrormarkdown',
    Bundle(assets.require('codemirror-markdown.css'),
        output='css/codemirror-markdown.packed.css', filters='cssmin'))
app.assets.register('js_ractive',
    Bundle(assets.require('ractive.js'),
        output='js/ractive.packed.js', filters='uglipyjs'))
app.assets.register('css_screens',
    Bundle(assets.require('screens.css'),
        output='css/screens.packed.css', filters='cssmin'))
app.assets.register('js_jquerysuccinct',
    Bundle(assets.require('!jquery.js', 'jquery.succinct.js'),
        output='js/jquerysuccinct.packed.js', filters='uglipyjs'))
app.assets.register('js_leaflet',
    Bundle(assets.require('leaflet.js'),
        output='js/leaflet.packed.js', filters='uglipyjs'))
app.assets.register('css_leaflet',
    Bundle(assets.require('leaflet.css'),
        output='css/leaflet.packed.css', filters='cssmin'))

baseframe.init_app(funnelapp, requires=['funnel'], ext_requires=[
    'pygments', 'toastr', 'baseframe-mui', 'fontawesome>=4.0.0',
    'jquery-easytabs'], theme='mui')
funnelapp.assets.register('js_fullcalendar',
    Bundle(assets.require('!jquery.js', 'jquery.fullcalendar.js', 'spectrum.js'),
        output='js/fullcalendar.packed.js', filters='uglipyjs'))
funnelapp.assets.register('css_fullcalendar',
    Bundle(assets.require('jquery.fullcalendar.css', 'spectrum.css', 'schedules.css'),
        output='css/fullcalendar.packed.css', filters='cssmin'))
funnelapp.assets.register('js_schedules',
    Bundle(assets.require('schedules.js'),
        output='js/schedules.packed.js', filters='uglipyjs'))
funnelapp.assets.register('js_codemirrormarkdown',
    Bundle(assets.require('codemirror-markdown.js'),
        output='js/codemirror-markdown.packed.js', filters='uglipyjs'))
funnelapp.assets.register('css_codemirrormarkdown',
    Bundle(assets.require('codemirror-markdown.css'),
        output='css/codemirror-markdown.packed.css', filters='cssmin'))
funnelapp.assets.register('js_ractive',
    Bundle(assets.require('ractive.js'),
        output='js/ractive.packed.js', filters='uglipyjs'))
funnelapp.assets.register('css_screens',
    Bundle(assets.require('screens.css'),
        output='css/screens.packed.css', filters='cssmin'))
funnelapp.assets.register('js_jquerysuccinct',
    Bundle(assets.require('!jquery.js', 'jquery.succinct.js'),
        output='js/jquerysuccinct.packed.js', filters='uglipyjs'))
funnelapp.assets.register('js_leaflet',
    Bundle(assets.require('leaflet.js', 'leaflet-search.js'),
        output='js/leaflet.packed.js', filters='uglipyjs'))
funnelapp.assets.register('css_leaflet',
    Bundle(assets.require('leaflet.css', 'leaflet-search.css'),
        output='css/leaflet.packed.css', filters='cssmin'))

# FIXME: Hack for external build system generating relative /static URLs.
# Fix this by generating absolute URLs to the static subdomain during build.
funnelapp.add_url_rule('/static/<path:filename>', endpoint='static',
    view_func=funnelapp.send_static_file, subdomain=None)
funnelapp.add_url_rule('/static/<path:filename>', endpoint='static',
    view_func=funnelapp.send_static_file, subdomain='<subdomain>')
