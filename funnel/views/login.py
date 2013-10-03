# -*- coding: utf-8 -*-

from flask import flash, redirect, render_template
from coaster.views import get_next_url
from baseframe import _

from .. import app, lastuser
from ..models import db


@app.route('/login')
@lastuser.login_handler
def login():
    return {'scope': 'id email phone'}


@app.route('/logout')
@lastuser.logout_handler
def logout():
    flash(_("You are now logged out"), category='info')
    return get_next_url()


@app.route('/login/redirect')
@lastuser.auth_handler
def lastuserauth():
    # Save the user object
    db.session.commit()
    return redirect(get_next_url())


@app.route('/login/notify', methods=['POST'])
@lastuser.notification_handler
def lastusernotify(user):
    # Save the user object
    db.session.commit()


@lastuser.auth_error_handler
def lastuser_error(error, error_description=None, error_uri=None):
    if error == 'access_denied':
        flash("You denied the request to login", category='error')
        return redirect(get_next_url())
    return render_template("autherror.html",
        error=error,
        error_description=error_description,
        error_uri=error_uri)
