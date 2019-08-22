# -*- coding: utf-8 -*-

import six

from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from flask import (
    Response,
    current_app,
    jsonify,
    make_response,
    redirect,
    request,
    url_for,
)

import unicodecsv

from baseframe import _
from coaster.auth import current_auth
from coaster.utils import getbool, make_name, midnight_to_utc, utcnow
from coaster.views import ClassView, render_with, requestargs, route

from .. import app, funnelapp, lastuser
from ..models import ContactExchange, Participant, Project, db
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

    def get_project(self, suuid):
        return (
            Project.query.filter_by(suuid=suuid)
            .options(db.load_only(Project.id, Project.uuid, Project.title))
            .one_or_404()
        )

    @route('', endpoint='contacts')
    @lastuser.requires_login
    @render_with('contacts.html.jinja2')
    def contacts(self):
        """Grouped list of contacts"""
        archived = getbool(request.args.get('archived'))
        return {
            'contacts': ContactExchange.grouped_counts_for(
                current_auth.user, archived=archived
            )
        }

    def contacts_to_csv(self, contacts, timezone, filename):
        """
        Returns a CSV of given contacts
        """
        outfile = six.BytesIO()
        out = unicodecsv.writer(outfile, encoding='utf-8')
        out.writerow(
            [
                'scanned_at',
                'fullname',
                'email',
                'phone',
                'twitter',
                'job_title',
                'company',
                'city',
            ]
        )
        for contact in contacts:
            proxy = contact.current_access()
            participant = proxy.participant
            out.writerow(
                [
                    proxy.scanned_at.astimezone(timezone)
                    .replace(second=0, microsecond=0, tzinfo=None)
                    .isoformat(),  # Strip precision from timestamp
                    participant.fullname,
                    participant.email,
                    participant.phone,
                    participant.twitter,
                    participant.job_title,
                    participant.company,
                    participant.city,
                ]
            )

        outfile.seek(0)
        return Response(
            six.text_type(outfile.getvalue(), 'utf-8'),
            content_type='text/csv',
            headers=[
                (
                    'Content-Disposition',
                    'attachment;filename="{filename}.csv"'.format(filename=filename),
                )
            ],
        )

    @route('<suuid>/<datestr>.csv', endpoint='contacts_project_date_csv')
    @lastuser.requires_login
    def project_date_csv(self, suuid, datestr):
        """Contacts for a given project and date in CSV format"""
        archived = getbool(request.args.get('archived'))
        project = self.get_project(suuid)
        date = datetime.strptime(datestr, '%Y-%m-%d').date()

        contacts = ContactExchange.contacts_for_project_and_date(
            current_auth.user, project, date, archived
        )
        return self.contacts_to_csv(
            contacts,
            timezone=project.timezone,
            filename='contacts-{project}-{date}'.format(
                project=make_name(project.title), date=date.strftime('%Y%m%d')
            ),
        )

    @route('<suuid>.csv', endpoint='contacts_project_csv')
    @lastuser.requires_login
    def project_csv(self, suuid):
        """Contacts for a given project in CSV format"""
        archived = getbool(request.args.get('archived'))
        project = self.get_project(suuid)

        contacts = ContactExchange.contacts_for_project(
            current_auth.user, project, archived
        )
        return self.contacts_to_csv(
            contacts,
            timezone=project.timezone,
            filename='contacts-{project}'.format(project=make_name(project.title)),
        )

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
            return make_response(
                jsonify(status='error', message=u"Attendee details not found"), 404
            )
        project = participant.project
        if project.schedule_end_at:
            if (
                midnight_to_utc(
                    project.schedule_end_at + timedelta(days=1), project.timezone
                )
                < utcnow()
            ):
                return make_response(
                    jsonify(status='error', message=_(u"This project has concluded")),
                    403,
                )

            try:
                contact_exchange = ContactExchange(
                    user=current_auth.actor, participant=participant
                )
                db.session.add(contact_exchange)
                db.session.commit()
            except IntegrityError:
                current_app.logger.warning(u"Contact already scanned")
                db.session.rollback()
            return jsonify(contact=contact_details(participant))
        else:
            return make_response(
                jsonify(status='error', message=u"Unauthorized contact exchange"), 403
            )


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
