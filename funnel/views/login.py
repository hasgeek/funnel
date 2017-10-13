# -*- coding: utf-8 -*-

from flask import g, flash, redirect, render_template
from coaster.views import get_next_url
from baseframe import _

from .. import app, lastuser
from ..models import db, Profile


@app.route('/login')
@lastuser.login_handler
def login():
    return {'scope': 'id email phone organizations teams'}


@app.route('/logout')
@lastuser.logout_handler
def logout():
    flash(_("You are now logged out"), category='info')
    return get_next_url()


@app.route('/login/redirect')
@lastuser.auth_handler
def lastuserauth():
    Profile.update_from_user(g.user, db.session, make_user_profiles=False, make_org_profiles=False)
    db.session.commit()
    return redirect(get_next_url())


@app.route('/login/notify', methods=['POST'])
@lastuser.notification_handler
def lastusernotify(user):
    Profile.update_from_user(user, db.session, make_user_profiles=False, make_org_profiles=False)
    db.session.commit()


@lastuser.auth_error_handler
def lastuser_error(error, error_description=None, error_uri=None):
    if error == 'access_denied':
        flash("You denied the request to login", category='error')
        return redirect(get_next_url())
    return render_template("autherror.html.jinja2",
        error=error,
        error_description=error_description,
        error_uri=error_uri)
