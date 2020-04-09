# -*- coding: utf-8 -*-

from flask import redirect, url_for

from coaster.auth import current_auth
from coaster.views import ClassView, render_with, route

from .. import app, funnelapp
from ..forms import EmailPrimaryForm, PhonePrimaryForm
from ..registry import login_registry
from .helpers import requires_login


@route('/account')
class AccountView(ClassView):
    current_section = 'account'  # needed for showing active tab

    @route('', endpoint='account')
    @requires_login
    @render_with('account.html.jinja2')
    def account(self):
        primary_email_form = EmailPrimaryForm()
        primary_phone_form = PhonePrimaryForm()
        service_forms = {}
        for service, provider in login_registry.items():
            if provider.at_login and provider.form is not None:
                service_forms[service] = provider.get_form()
        return {
            'user': current_auth.user.current_access(),
            'primary_email_form': primary_email_form,
            'primary_phone_form': primary_phone_form,
            'service_forms': service_forms,
            'login_registry': login_registry,
        }

    @route('saved', endpoint='saved')
    @requires_login
    @render_with('account_saved.html.jinja2')
    def saved(self):
        return {'saved_projects': current_auth.user.saved_projects}


@route('/account')
class FunnelAccountView(ClassView):
    @route('', endpoint='account')
    @requires_login
    def account(self):
        with app.app_context(), app.test_request_context():
            return redirect(url_for('account', _external=True))


AccountView.init_app(app)
FunnelAccountView.init_app(funnelapp)
