#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import coaster.app
from flask import Flask
from flask.ext.mail import Mail
from flask.ext.lastuser import Lastuser
from flask.ext.lastuser.sqlalchemy import UserManager
from baseframe import baseframe, assets, Version, Bundle
from ._version import __version__


app = Flask(__name__, instance_relative_config=True)
mail = Mail()
lastuser = Lastuser()


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

from . import models, forms, workflows, views  # NOQA
from .models import db


# --- Configuration------------------------------------------------------------

def init_for(env):
    coaster.app.init_app(app, env)
    db.init_app(app)
    db.app = app

    mail.init_app(app)
    lastuser.init_app(app)
    lastuser.init_usermanager(UserManager(db, models.User, models.Team))
    baseframe.init_app(app, requires=['funnel'], ext_requires=[
        ('codemirror-markdown', 'pygments'), 'toastr', 'baseframe-bs3', 'fontawesome>=4.0.0'
        ])
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
