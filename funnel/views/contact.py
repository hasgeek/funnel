"""Views for scanned contacts, available under account settings."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from io import StringIO

from flask import Response, current_app, render_template, request
from sqlalchemy.exc import IntegrityError

from baseframe import _
from coaster.utils import getbool, make_name, midnight_to_utc, utcnow
from coaster.views import ClassView, render_with, requestargs, route

from .. import app
from ..auth import current_auth
from ..models import ContactExchange, Project, TicketParticipant, db, sa_orm
from ..typing import ReturnRenderWith, ReturnView
from ..utils import format_twitter_handle
from .login_session import requires_login


def contact_details(ticket_participant: TicketParticipant) -> dict[str, str | None]:
    return {
        'fullname': ticket_participant.fullname,
        'company': ticket_participant.company,
        'email': ticket_participant.email,
        'twitter': format_twitter_handle(ticket_participant.twitter),
        'phone': ticket_participant.phone,
    }


@route('/account/contacts', init_app=app)
class ContactView(ClassView):
    current_section = 'account'

    def get_project(self, uuid_b58):
        return (
            Project.query.filter_by(uuid_b58=uuid_b58)
            .options(sa_orm.load_only(Project.id, Project.uuid, Project.title))
            .one_or_404()
        )

    @route('', endpoint='contacts')
    @requires_login
    @render_with('contacts.html.jinja2')
    def contacts(self) -> ReturnRenderWith:
        """Return contacts grouped by project and date."""
        archived = getbool(request.args.get('archived')) or False
        return {
            'contacts': ContactExchange.grouped_counts_for(
                current_auth.user, archived=archived
            )
        }

    def contacts_to_csv(self, contacts, timezone, filename):
        """Return a CSV of given contacts."""
        outfile = StringIO(newline='')
        out = csv.writer(outfile)
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
            ticket_participant = proxy.ticket_participant
            out.writerow(
                [
                    proxy.scanned_at.astimezone(timezone)
                    .replace(second=0, microsecond=0, tzinfo=None)
                    .isoformat(),  # Strip precision from timestamp
                    ticket_participant.fullname,
                    ticket_participant.email,
                    ticket_participant.phone,
                    ticket_participant.twitter,
                    ticket_participant.job_title,
                    ticket_participant.company,
                    ticket_participant.city,
                ]
            )

        outfile.seek(0)
        return Response(
            outfile.getvalue(),
            content_type='text/csv',
            headers=[
                (
                    'Content-Disposition',
                    f'attachment;filename="{filename}.csv"',
                )
            ],
        )

    @route('<uuid_b58>/<datestr>.csv', endpoint='contacts_project_date_csv')
    @requires_login
    def project_date_csv(self, uuid_b58: str, datestr: str) -> ReturnView:
        """Return contacts for a given project and date in CSV format."""
        archived = getbool(request.args.get('archived')) or False
        project = self.get_project(uuid_b58)
        date = datetime.strptime(datestr, '%Y-%m-%d').date()

        contacts = ContactExchange.contacts_for_project_and_date(
            current_auth.user, project, date, archived
        )
        return self.contacts_to_csv(
            contacts,
            timezone=project.timezone,
            filename=f'contacts-{make_name(project.title)}-{date.strftime("%Y%m%d")}',
        )

    @route('<uuid_b58>.csv', endpoint='contacts_project_csv')
    @requires_login
    def project_csv(self, uuid_b58: str) -> ReturnView:
        """Return contacts for a given project in CSV format."""
        archived = getbool(request.args.get('archived')) or False
        project = self.get_project(uuid_b58)

        contacts = ContactExchange.contacts_for_project(
            current_auth.user, project, archived
        )
        return self.contacts_to_csv(
            contacts,
            timezone=project.timezone,
            filename=f'contacts-{make_name(project.title)}',
        )

    @route('scan', endpoint='scan_contact')
    @requires_login
    def scan(self) -> ReturnView:
        """Scan a badge."""
        return render_template('scan_contact.html.jinja2')

    @route('scan/connect', endpoint='scan_connect', methods=['POST'])
    @requires_login
    @requestargs('puk', 'key')
    def connect(self, puk: str, key: str) -> ReturnView:
        """Verify a badge scan and create a contact."""
        ticket_participant = TicketParticipant.query.filter_by(puk=puk, key=key).first()
        if ticket_participant is None:
            # FIXME: when status='error', message should be in `error_description`
            return {
                'status': 'error',
                'error': '404',
                'message': _("Attendee details not found"),
            }, 404

        project = ticket_participant.project
        if project.end_at:
            if (
                midnight_to_utc(project.end_at + timedelta(days=1), project.timezone)
                < utcnow()
            ):
                # FIXME: when status='error', message should be in `error_description`
                return {
                    'status': 'error',
                    'error': '410',
                    'message': _("This project has concluded"),
                }, 410

            try:
                contact_exchange = ContactExchange(
                    account=current_auth.actor, ticket_participant=ticket_participant
                )
                db.session.add(contact_exchange)
                db.session.commit()
            except IntegrityError:
                current_app.logger.warning("Contact already scanned")
                db.session.rollback()
            return {'status': 'ok', 'contact': contact_details(ticket_participant)}
        # FIXME: when status='error', message should be in `error_description`
        return {
            'status': 'error',
            'error': '403',
            'message': _("Unauthorized contact exchange"),
        }, 403
