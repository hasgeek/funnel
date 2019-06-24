# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from flask import request, jsonify, make_response, current_app, url_for, redirect
from sqlalchemy.exc import IntegrityError

from coaster.auth import current_auth
from coaster.views import requestargs, ClassView, route, render_with
from coaster.utils import midnight_to_utc, utcnow, getbool

from baseframe import _

from .. import app, funnelapp, lastuser
from ..models import (db, Participant, ContactExchange, Project)
from ..util import format_twitter_handle


def contact_details(participant):
    if participant:
        return {
            'fullname': participant.fullname,
            'company': participant.company,
            'email': participant.email,
            'twitter': format_twitter_handle(participant.twitter),
            'phone': participant.phone,
            }


@route('/account/contacts')
class ContactView(ClassView):
    current_section = 'contact'

    def get_project_and_date(self, suuid, datestr):
        if suuid is not None:
            project = Project.query.filter_by(suuid=suuid).options(db.load_only(Project.id, Project.title)).one_or_404()
        else:
            project = None
        dt = datetime.strptime(datestr, '%Y%m%d')
        return project, dt.date()

    @route('', endpoint='contacts')
    @lastuser.requires_login
    @render_with('contacts.html.jinja2')
    def contacts(self):
        """List of contacts"""
        archived = getbool(request.args.get('archived'))
        return {'contacts': ContactExchange.grouped_counts_for(current_auth.user, archived=archived)}

    @route('scan', endpoint='scan_contact')
    @lastuser.requires_login
    @render_with('scan_contact.html.jinja2')
    def scan(self):
        """Scan a badge"""
        return {}

    @route('scan/connect', endpoint='scan_connect', methods=['POST'])
    @lastuser.requires_login
    @requestargs('puk', 'key')
    def connect(self, puk, key):
        """Scan verification"""
        participant = Participant.query.filter_by(puk=puk, key=key).first()
        if not participant:
            return make_response(jsonify(status='error',
                message=u"Attendee details not found"), 404)
        project = participant.project
        if project.date_upto:
            if midnight_to_utc(project.date_upto + timedelta(days=1), project.timezone) < utcnow():
                return make_response(jsonify(status='error',
                    message=_(u"This project has concluded")), 403)

            try:
                contact_exchange = ContactExchange(user=current_auth.actor,
                    participant=participant)
                db.session.add(contact_exchange)
                db.session.commit()
            except IntegrityError:
                current_app.logger.warning(u"Contact already scanned")
                db.session.rollback()
            return jsonify(contact=contact_details(participant))
        else:
            return make_response(jsonify(status='error',
                message=u"Unauthorized contact exchange"), 403)


@route('/account/contacts')
class FunnelContactView(ClassView):
    @route('', endpoint='contacts')
    def contacts(self):
        with app.app_context(), app.test_request_context():
            return redirect(url_for('contacts', _external=True))

    @route('', endpoint='scan_contact')
    def scan(self):
        with app.app_context(), app.test_request_context():
            return redirect(url_for('scan_contact', _external=True))


ContactView.init_app(app)
FunnelContactView.init_app(funnelapp)
