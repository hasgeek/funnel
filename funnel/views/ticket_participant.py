from sqlalchemy.exc import IntegrityError

from flask import abort, flash, g, jsonify, redirect, request, url_for

from baseframe import _, forms, request_is_xhr
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

from .. import app, funnelapp
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
from ..utils import abort_null, format_twitter_handle, make_qrcode, split_name
from .decorators import legacy_redirect
from .helpers import mask_email
from .login_session import requires_login
from .mixins import ProjectViewMixin, TicketEventViewMixin


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
                    "{puk}{key}".format(
                        puk=ticket_participant.puk, key=ticket_participant.key
                    )
                ),
                'order_no': ticket.order_no if ticket else '',
            }
        )
    return badges


def ticket_participant_data(ticket_participant, project_id, full=False):
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
    }
    if not {'concierge', 'usher'}.isdisjoint(project.current_roles):
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
    __decorators__ = [legacy_redirect]

    @route('json')
    @requires_login
    @requires_roles({'concierge', 'usher'})
    def participants_json(self):
        return jsonify(
            ticket_participants=[
                ticket_participant_data(ticket_participant, self.obj.id)
                for ticket_participant in self.obj.ticket_participants
            ]
        )

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'concierge'})
    def new_participant(self):
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
                flash(_("This participant already exists."), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(
            form=form, title=_("New ticketed participant"), submit=_("Add participant")
        )


@route('/<project>/ticket_participants', subdomain='<profile>')
class FunnelProjectTicketParticipantView(ProjectTicketParticipantView):
    pass


ProjectTicketParticipantView.init_app(app)
FunnelProjectTicketParticipantView.init_app(funnelapp)


@TicketParticipant.views('main')
@route('/<profile>/<project>/ticket_participant/<ticket_participant>')
class TicketParticipantView(UrlForView, ModelView):
    __decorators__ = [legacy_redirect, requires_login]

    model = TicketParticipant
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'ticket_participant': 'uuid_b58',
    }

    def loader(self, profile, project, ticket_participant):
        ticket_participant = (
            self.model.query.join(Project, Profile)
            .filter(
                db.func.lower(Profile.name) == db.func.lower(profile),
                Project.name == project,
                TicketParticipant.uuid_b58 == ticket_participant,
            )
            .first_or_404()
        )
        return ticket_participant

    def after_loader(self):
        g.profile = self.obj.project.profile
        return super(TicketParticipantView, self).after_loader()

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'project_concierge'})
    def edit(self):
        form = TicketParticipantForm(obj=self.obj, parent=self.obj.project)
        if form.validate_on_submit():
            self.obj.user = form.user
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_(u"Your changes have been saved"), 'info')
            return redirect(self.obj.project.url_for('admin'), code=303)
        return render_form(
            form=form, title=_(u"Edit Participant"), submit=_(u"Save changes")
        )

    @route('badge', methods=['GET'])
    @render_with('badge.html.jinja2')
    @requires_roles({'project_concierge', 'project_usher'})
    def badge(self):
        return {'badges': ticket_participant_badge_data([self.obj], self.obj.project)}

    @route('label_badge', methods=['GET'])
    @render_with('label_badge.html.jinja2')
    @requires_roles({'project_concierge', 'project_usher'})
    def label_badge(self):
        return {'badges': ticket_participant_badge_data([self.obj], self.obj.project)}


@route('/<project>/ticket_participant/<uuid_b58>', subdomain='<profile>')
class FunnelTicketParticipantView(TicketParticipantView):
    pass


TicketParticipantView.init_app(app)
FunnelTicketParticipantView.init_app(funnelapp)


@TicketEvent.views('ticket_participant')
@route('/<profile>/<project>/ticket_event/<name>')
class TicketEventParticipantView(TicketEventViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect, requires_login]

    @route('ticket_participants/checkin', methods=['GET', 'POST'])
    @requires_roles({'project_concierge', 'project_usher'})
    def checkin(self):
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
            if request_is_xhr():
                return jsonify(
                    status=True,
                    ticket_participant_ids=ticket_participant_ids,
                    checked_in=checked_in,
                )
        return redirect(self.obj.url_for('view'), code=303)

    @route('ticket_participants/json')
    @render_with(json=True)
    @requires_roles({'project_concierge', 'project_usher'})
    def participants_json(self):
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
            'ticket_participants': ticket_participants,
            'total_participants': len(ticket_participants),
            'total_checkedin': checkin_count,
        }

    @route('badges')
    @render_with('badge.html.jinja2')
    @requires_roles({'project_concierge', 'project_usher'})
    def badges(self):
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
    @requires_roles({'project_concierge', 'project_usher'})
    def label_badges(self):
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


@route('/<project>/ticket_event/<name>', subdomain='<profile>')
class FunnelTicketEventParticipantView(TicketEventParticipantView):
    pass


TicketEventParticipantView.init_app(app)
FunnelTicketEventParticipantView.init_app(funnelapp)


# FIXME: make this endpoint use uuid_b58 instead of puk, along with badge generation
@route('/<profile>/<project>/event/<event>/ticket_participant/<puk>')
class TicketEventParticipantCheckinView(ClassView):
    __decorators__ = [requires_login]

    @route('checkin', methods=['POST'])
    @render_with(json=True)
    def checkin_puk(self, profile, project, ticket_event, puk):
        abort(403)

        checked_in = getbool(request.form.get('checkin', 't'))
        ticket_event = (
            TicketEvent.query.join(Project, Profile)
            .filter(
                db.func.lower(Profile.name) == db.func.lower(profile),
                Project.name == project,
                TicketEvent.name == ticket_event,
            )
            .first_or_404()
        )
        ticket_participant = (
            TicketParticipant.query.join(Project, Profile)
            .filter(
                db.func.lower(Profile.name) == db.func.lower(profile),
                Project.name == project,
                TicketParticipant.puk == puk,
            )
            .first_or_404()
        )
        attendee = TicketEventParticipant.get(ticket_event, ticket_participant.uuid_b58)
        if not attendee:
            return (
                {'error': 'not_found', 'error_description': "Attendee not found"},
                404,
            )
        attendee.checked_in = checked_in
        db.session.commit()
        return {'attendee': {'fullname': ticket_participant.fullname}}


TicketEventParticipantCheckinView.init_app(app)
