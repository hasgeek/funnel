# -*- coding: utf-8 -*-

from flask import redirect, url_for

from coaster.auth import current_auth
from coaster.views import ClassView, render_with, route

from .. import app, funnelapp, lastuser


@route('/account')
class AccountView(ClassView):
    current_section = 'account'  # needed for showing active tab

    @route('', endpoint='account')
    @lastuser.requires_login
    @render_with('account.html.jinja2')
    def account(self):
        return {'user': current_auth.user.current_access()}


@route('/my_saves')
class SavesView(ClassView):
    current_section = 'saves'  # needed for showing active tab

    @route('', endpoint='my_saves')
    @lastuser.requires_login
    @render_with('my_saves.html.jinja2')
    def my_saves(self):
        return {'saved_projects': current_auth.user.saved_projects}


@route('/account')
class FunnelAccountView(ClassView):
    @route('', endpoint='account')
    @lastuser.requires_login
    def account(self):
        with app.app_context(), app.test_request_context():
            return redirect(url_for('account', _external=True))


AccountView.init_app(app)
SavesView.init_app(app)
FunnelAccountView.init_app(funnelapp)
