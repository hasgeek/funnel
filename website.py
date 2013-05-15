#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import coaster.app
from flask.ext.mail import Mail
from flask.ext.lastuser import Lastuser
from flask.ext.lastuser.sqlalchemy import UserManager
from baseframe import baseframe, assets, Version
from _version import __version__

from app import app
mail = Mail()
lastuser = Lastuser()


# --- Assets ------------------------------------------------------------------

version = Version(__version__)
assets['jquery.oembed.js'][version] = 'js/libs/jquery.oembed.js'
assets['showdown.js'][version] = 'js/libs/showdown.js'
assets['funnel.js'][version] = 'js/scripts.js'
assets['funnel.css'][version] = 'css/screen.css'

# --- Import rest of the app --------------------------------------------------

import models, forms, views


# --- Configuration------------------------------------------------------------

def init_for(env):
    coaster.app.init_app(app, env)
    mail.init_app(app)
    lastuser.init_app(app)
    lastuser.init_usermanager(UserManager(models.db, models.User))
    baseframe.init_app(app, requires=[
        'jquery', 'jquery.form', 'jquery.oembed', 'showdown', 'baseframe-networkbar', 'funnel'
        ])
