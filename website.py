#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from flask.ext.assets import Environment, Bundle

from app import app
app.config.from_object(__name__)
try:
    app.config.from_object('settings')
except ImportError:
    import sys
    print >> sys.stderr, "Please create a settings.py with the necessary settings. See settings-sample.py."
    print >> sys.stderr, "You may use the site without these settings, but some features may not work."


# --- Assets ------------------------------------------------------------------

assets = Environment(app)
js = Bundle('js/libs/jquery-1.5.1.min.js',
            'js/libs/jquery.form.js',
            'js/libs/jquery.oembed.js',
            'js/libs/jquery.tablesorter.min.js',
            'js/libs/showdown.js',
            'js/scripts.js',
            filters='jsmin', output='js/packed.js')

assets.register('js_all', js)

# --- Import rest of the app --------------------------------------------------

import models, forms, views


# --- Logging -----------------------------------------------------------------

file_handler = logging.FileHandler(app.config['LOGFILE'])
file_handler.setLevel(logging.WARNING)
app.logger.addHandler(file_handler)
if app.config['ADMINS']:
    import logging.handlers
    mail_handler = logging.handlers.SMTPHandler(app.config['MAIL_SERVER'],
        app.config['DEFAULT_MAIL_SENDER'][1],
        app.config['ADMINS'],
        'funnel failure',
        credentials = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD']))
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)


if __name__ == '__main__':
    models.db.create_all()
    app.run('0.0.0.0', port=3000, debug=True)
