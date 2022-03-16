from __future__ import annotations
from os import access

from typing import NamedTuple
import os.path

from flask import Response, g, jsonify, render_template, url_for, request, flash

from baseframe import _, __
from baseframe.filters import date_filter
from coaster.auth import current_auth
from coaster.utils import getbool, make_name
from coaster.views import (
    ClassView,
    ModelView,
    UrlChangeCheck,
    UrlForView,
    get_next_url,
    render_with,
    requires_roles,
    route,
)
from werkzeug.utils import redirect
from .login_session import requires_login

from .. import app, pages
from ..forms import SavedProjectForm
from ..models import Project, db, UserMeetingCredentials


@route('/account/meeting-credentials')
class MeetingCredentialView(ClassView):
    current_section = 'meeting_credentials'
    __decorators__ = [requires_login]


    @route('', endpoint='meeting_credentials', methods=['GET','POST'])
    def meeting_credentials(self):
        if request.method == "POST":
            access_key = request.form.get("access_key")
            secret_key = request.form.get("secret_key")
            provider = request.form.get("provider")
            user_meeting_credentials = UserMeetingCredentials(access_key=access_key, secret_key=secret_key, user_id=current_auth.user.id, provider=provider)
            db.session.add(user_meeting_credentials)
            db.session.commit()
            flash('Credentials Added successfully')
            return redirect(url_for('meeting_credentials'))

        if request.method == "GET":
            credentials = UserMeetingCredentials.query.filter_by(user_id=current_auth.user.id).order_by(UserMeetingCredentials.date_created).all()
            return render_template('meeting_credentials.html.jinja2', credentials=credentials)


    @route('edit', methods=['POST'])
    def edit_meeting_credentials(self):
        if request.method == "POST":
            new_access_key = request.form.get("access_key")
            new_secret_key = request.form.get("secret_key")
            user_meeting_credentials = UserMeetingCredentials.query.filter_by(user_id=current_auth.user.id).first()
            user_meeting_credentials.access_key = new_access_key
            user_meeting_credentials.secret_key = new_secret_key
            db.session.commit()
            flash('Credentials edited successfully')
            return redirect(url_for('meeting_credentials'))


    @route('toggle', methods=['POST'], endpoint='toggle_meeting_credentials')
    def toggle_meeting_credentials(self):
        if request.method == "POST":
            id = int(request.form.get("activate"))
            user_meeting_credentials = UserMeetingCredentials.query.filter_by(user_id=current_auth.user.id).all()
            for i in user_meeting_credentials:
                if i.id == id:
                    i.is_active ^= True
                else:
                    i.is_active = False
            db.session.commit()
            return redirect(url_for('meeting_credentials'))

    @route('delete', methods=['POST'], endpoint='delete_meeting_credentials')
    def delete_meeting_credentials(self):
        if request.method == "POST":
            id = request.form.get("delete")
            user_meeting_credentials = UserMeetingCredentials.query.filter_by(id=id).first()
            user_meeting_credentials.is_active = False
            user_meeting_credentials.is_deleted = True
            db.session.commit()
            flash('Credentials deleted successfully')
            return redirect(url_for('meeting_credentials'))

MeetingCredentialView.init_app(app) 