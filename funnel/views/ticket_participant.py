"""Views for ticketed participants synced from a ticketing provider."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.exc import IntegrityError

from flask import abort, flash, request, url_for

from baseframe import _, forms
from baseframe.forms import render_form
from coaster.utils import getbool, uuid_to_base58
from coaster.views import (
    ClassView,
    ModelView,
    UrlForView,
    render_with,
    requires_roles,
    route,
)

from .. import app
from ..forms import TicketParticipantForm
from ..models import (
    Profile,
    Project,
    SyncTicket,
    TicketEvent,
    TicketEventParticipant,
    TicketParticipant,
    db,
)
from ..proxies import request_wants
from ..typing import ReturnRenderWith, ReturnView
from ..utils import (
    abort_null,
    format_twitter_handle,
    make_qrcode,
    mask_email,
    split_name,
)
from .helpers import render_redirect
from .login_session import requires_login
from .mixins import ProfileCheckMixin, ProjectViewMixin, TicketEventViewMixin


def ticket_participant_badge_data(ticket_participants, project):
    badges = []
    for ticket_participant in ticket_participants:
        first_name, last_name = split_name(ticket_participant.fullname)
        ticket = SyncTicket.query.filter_by(
            ticket_participant=ticket_participant
        ).first()
        badges.append(
            {
                'first_name': first_name,
                'last_name': last_name,
                'twitter': format_twitter_handle(ticket_participant.twitter),
                'company': ticket_participant.company,
                'qrcode_content': make_qrcode(
                    f'{ticket_participant.puk}{ticket_participant.key}'
                ),
                'order_no': ticket.order_no if ticket is not None else '',
            }
        )
    return badges


# FIXME: Do not process integer primary keys
def ticket_participant_data(
    ticket_participant: TicketParticipant, project_id: int, full=False
):
    data = {
        '_id': ticket_participant.id,
        'puk': ticket_participant.puk,
        'fullname': ticket_participant.fullname,
        'job_title': ticket_participant.job_title,
        'company': ticket_participant.company,
        'project_id': project_id,
    }
    if full:
        data.update(
            {
                'email': ticket_participant.email,
                'twitter': ticket_participant.twitter,
                'phone': ticket_participant.phone,
            }
        )
    return data


def ticket_participant_checkin_data(ticket_participant, project, ticket_event):
    puuid_b58 = uuid_to_base58(ticket_participant.uuid)
    data = {
        'puuid_b58': puuid_b58,
        'fullname': ticket_participant.fullname,
        'company': ticket_participant.company,
        'email': mask_email(ticket_participant.email),
        'badge_printed': ticket_participant.badge_printed,
        'checked_in': ticket_participant.checked_in,
        'ticket_type_titles': ticket_participant.ticket_type_titles,
        'has_user': ticket_participant.has_user,
    }
    if not {'promoter', 'usher'}.isdisjoint(project.current_roles):
        data.update(
            {
                'badge_url': url_for(
                    'TicketParticipantView_badge',
                    profile=project.profile.name,
                    project=project.name,
                    ticket_participant=puuid_b58,
                ),
                'label_badge_url': url_for(
                    'TicketParticipantView_label_badge',
                    profile=project.profile.name,
                    project=project.name,
                    ticket_participant=puuid_b58,
                ),
                'edit_url': url_for(
                    'TicketParticipantView_edit',
                    profile=project.profile.name,
                    project=project.name,
                    ticket_participant=puuid_b58,
                ),
            }
        )
    return data


@Project.views('ticket_participant')
@route('/<profile>/<project>/ticket_participants')
class ProjectTicketParticipantView(ProjectViewMixin, UrlForView, ModelView):
    @route('json')
    @requires_login
    @requires_roles({'promoter', 'usher'})
    def participants_json(self) -> ReturnView:
        return {
            'status': 'ok',
            'ticket_participants': [
                ticket_participant_data(ticket_participant, self.obj.id)
                for ticket_participant in self.obj.ticket_participants
            ],
        }

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'promoter'})
    def new_participant(self) -> ReturnView:
        form = TicketParticipantForm(parent=self.obj)
        if form.validate_on_submit():
            ticket_participant = TicketParticipant(project=self.obj)
            ticket_participant.user = form.user
            with db.session.no_autoflush:
                form.populate_obj(ticket_participant)
            try:
                db.session.add(ticket_participant)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(_("This participant already exists"), 'info')
            return render_redirect(self.obj.url_for('admin'))
        return render_form(
            form=form, title=_("New ticketed participant"), submit=_("Add participant")
        )


ProjectTicketParticipantView.init_app(app)


@TicketParticipant.views('main')
@route('/<profile>/<project>/ticket_participant/<ticket_participant>')
class TicketParticipantView(ProfileCheckMixin, UrlForView, ModelView):
    __decorators__ = [requires_login]

    model = TicketParticipant
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'ticket_participant': 'uuid_b58',
    }
    obj: TicketParticipant

    def loader(self, profile, project, ticket_participant) -> TicketParticipant:
        return (
            TicketParticipant.query.join(Project)
            .join(Profile)
            .filter(
                Profile.name_is(profile),
                Project.name == project,
                TicketParticipant.uuid_b58 == ticket_participant,
            )
            .first_or_404()
        )

    def after_loader(self) -> Optional[ReturnView]:
        self.profile = self.obj.project.account
        return super().after_loader()

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'project_promoter'})
    def edit(self) -> ReturnView:
        form = TicketParticipantForm(obj=self.obj, parent=self.obj.project)
        if form.validate_on_submit():
            self.obj.user = form.user
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return render_redirect(self.obj.project.url_for('admin'))
        return render_form(
            form=form, title=_("Edit Participant"), submit=_("Save changes")
        )

    @route('badge', methods=['GET'])
    @render_with('badge.html.jinja2')
    @requires_roles({'project_promoter', 'project_usher'})
    def badge(self) -> ReturnRenderWith:
        return {'badges': ticket_participant_badge_data([self.obj], self.obj.project)}

    @route('label_badge', methods=['GET'])
    @render_with('label_badge.html.jinja2')
    @requires_roles({'project_promoter', 'project_usher'})
    def label_badge(self) -> ReturnRenderWith:
        return {'badges': ticket_participant_badge_data([self.obj], self.obj.project)}


TicketParticipantView.init_app(app)


@TicketEvent.views('ticket_participant')
@route('/<profile>/<project>/ticket_event/<name>')
class TicketEventParticipantView(TicketEventViewMixin, UrlForView, ModelView):
    __decorators__ = [requires_login]

    @route('ticket_participants/checkin', methods=['GET', 'POST'])
    @requires_roles({'project_promoter', 'project_usher'})
    def checkin(self) -> ReturnView:
        form = forms.Form()
        if form.validate_on_submit():
            checked_in = getbool(request.form.get('checkin'))
            ticket_participant_ids = [
                abort_null(x) for x in request.form.getlist('puuid_b58')
            ]
            for ticket_participant_id in ticket_participant_ids:
                attendee = TicketEventParticipant.get(self.obj, ticket_participant_id)
                attendee.checked_in = checked_in
            db.session.commit()
            if request_wants.json:
                return {
                    # FIXME: return 'status': 'ok'
                    'status': True,
                    'ticket_participant_ids': ticket_participant_ids,
                    'checked_in': checked_in,
                }
        return render_redirect(self.obj.url_for('view'))

    @route('ticket_participants/json')
    @requires_roles({'project_promoter', 'project_usher'})
    def participants_json(self) -> ReturnView:
        checkin_count = 0
        ticket_participants = []
        for ticket_participant in TicketParticipant.checkin_list(self.obj):
            ticket_participants.append(
                ticket_participant_checkin_data(
                    ticket_participant, self.obj.project, self.obj
                )
            )
            if ticket_participant.checked_in:
                checkin_count += 1

        return {
            'status': 'ok',
            'ticket_participants': ticket_participants,
            'total_participants': len(ticket_participants),
            'total_checkedin': checkin_count,
        }

    @route('badges')
    @render_with('badge.html.jinja2')
    @requires_roles({'project_promoter', 'project_usher'})
    def badges(self) -> ReturnRenderWith:
        badge_printed = getbool(request.args.get('badge_printed', 'f'))
        ticket_participants = (
            TicketParticipant.query.join(TicketEventParticipant)
            .filter(TicketEventParticipant.ticket_event_id == self.obj.id)
            .filter(TicketParticipant.badge_printed == badge_printed)
            .all()
        )
        return {
            'badge_template': self.obj.badge_template,
            'badges': ticket_participant_badge_data(
                ticket_participants, self.obj.project
            ),
        }

    @route('label_badges')
    @render_with('label_badge.html.jinja2')
    @requires_roles({'project_promoter', 'project_usher'})
    def label_badges(self) -> ReturnRenderWith:
        badge_printed = getbool(request.args.get('badge_printed', 'f'))
        ticket_participants = (
            TicketParticipant.query.join(TicketEventParticipant)
            .filter(TicketEventParticipant.ticket_event_id == self.obj.id)
            .filter(TicketParticipant.badge_printed == badge_printed)
            .all()
        )
        return {
            'badge_template': self.obj.badge_template,
            'badges': ticket_participant_badge_data(
                ticket_participants, self.obj.project
            ),
        }


TicketEventParticipantView.init_app(app)


# FIXME: make this endpoint use uuid_b58 instead of puk, along with badge generation
@route('/<profile>/<project>/event/<event>/ticket_participant/<puk>')
class TicketEventParticipantCheckinView(ClassView):
    __decorators__ = [requires_login]

    @route('checkin', methods=['POST'])
    def checkin_puk(
        self, profile: str, project: str, event: str, puk: str
    ) -> ReturnView:
        abort(403)

        checked_in = getbool(  # type: ignore[unreachable]
            request.form.get('checkin', 't')
        )
        ticket_event = (
            TicketEvent.query.join(Project)
            .join(Profile)
            .filter(
                Profile.name_is(profile),
                Project.name == project,
                TicketEvent.name == event,
            )
            .first_or_404()
        )
        ticket_participant = (
            TicketParticipant.query.join(Project)
            .join(Profile)
            .filter(
                Profile.name_is(profile),
                Project.name == project,
                TicketParticipant.puk == puk,
            )
            .first_or_404()
        )
        attendee = TicketEventParticipant.get(ticket_event, ticket_participant.uuid_b58)
        if attendee is None:
            return (
                {'error': 'not_found', 'error_description': _("Attendee not found")},
                404,
            )
        attendee.checked_in = checked_in
        db.session.commit()
        return {'attendee': {'fullname': ticket_participant.fullname}}


TicketEventParticipantCheckinView.init_app(app)
