from collections import namedtuple

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

EventParticipant = namedtuple('EventParticipant', ['event', 'participant'])


def ticket_participant_badge_data(participants, project):
    badges = []
    for participant in participants:
        first_name, last_name = split_name(participant.fullname)
        ticket = SyncTicket.query.filter_by(participant=participant).first()
        badges.append(
            {
                'first_name': first_name,
                'last_name': last_name,
                'twitter': format_twitter_handle(participant.twitter),
                'company': participant.company,
                'qrcode_content': make_qrcode(
                    "{puk}{key}".format(puk=participant.puk, key=participant.key)
                ),
                'order_no': ticket.order_no if ticket else '',
            }
        )
    return badges


def ticket_participant_data(participant, project_id, full=False):
    data = {
        '_id': participant.id,
        'puk': participant.puk,
        'fullname': participant.fullname,
        'job_title': participant.job_title,
        'company': participant.company,
        'project_id': project_id,
    }
    if full:
        data.update(
            {
                'email': participant.email,
                'twitter': participant.twitter,
                'phone': participant.phone,
            }
        )
    return data


def ticket_participant_checkin_data(participant, project, event):
    puuid_b58 = uuid_to_base58(participant.uuid)
    data = {
        'puuid_b58': puuid_b58,
        'fullname': participant.fullname,
        'company': participant.company,
        'email': mask_email(participant.email),
        'badge_printed': participant.badge_printed,
        'checked_in': participant.checked_in,
        'ticket_type_titles': participant.ticket_type_titles,
    }
    if not {'concierge', 'usher'}.isdisjoint(project.current_roles):
        data.update(
            {
                'badge_url': url_for(
                    'ParticipantView_badge',
                    profile=project.profile.name,
                    project=project.name,
                    participant=puuid_b58,
                ),
                'label_badge_url': url_for(
                    'ParticipantView_label_badge',
                    profile=project.profile.name,
                    project=project.name,
                    participant=puuid_b58,
                ),
                'edit_url': url_for(
                    'ParticipantView_edit',
                    profile=project.profile.name,
                    project=project.name,
                    participant=puuid_b58,
                ),
            }
        )
    return data


@Project.views('ticket_participant')
@route('/<profile>/<project>/participants')
class ProjectTicketParticipantView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('json')
    @requires_login
    @requires_roles({'concierge', 'usher'})
    def participants_json(self):
        return jsonify(
            participants=[
                ticket_participant_data(participant, self.obj.id)
                for participant in self.obj.participants
            ]
        )

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'concierge'})
    def new_participant(self):
        form = TicketParticipantForm(parent=self.obj)
        if form.validate_on_submit():
            participant = TicketParticipant(project=self.obj)
            participant.user = form.user
            with db.session.no_autoflush:
                form.populate_obj(participant)
            try:
                db.session.add(participant)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(_("This participant already exists."), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(
            form=form, title=_("New Participant"), submit=_("Add participant")
        )


@route('/<project>/participants', subdomain='<profile>')
class FunnelProjectTicketParticipantView(ProjectTicketParticipantView):
    pass


ProjectTicketParticipantView.init_app(app)
FunnelProjectTicketParticipantView.init_app(funnelapp)


@TicketParticipant.views('main')
@route('/<profile>/<project>/participant/<participant>')
class TicketParticipantView(UrlForView, ModelView):
    __decorators__ = [legacy_redirect, requires_login]

    model = TicketParticipant
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'participant': 'uuid_b58',
    }

    def loader(self, profile, project, participant):
        participant = (
            self.model.query.join(Project, Profile)
            .filter(
                db.func.lower(Profile.name) == db.func.lower(profile),
                Project.name == project,
                TicketParticipant.uuid_b58 == participant,
            )
            .first_or_404()
        )
        return participant

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


@route('/<project>/participant/<uuid_b58>', subdomain='<profile>')
class FunnelTicketParticipantView(TicketParticipantView):
    pass


TicketParticipantView.init_app(app)
FunnelTicketParticipantView.init_app(funnelapp)


@TicketEvent.views('participant')
@route('/<profile>/<project>/event/<name>')
class TicketEventParticipantView(TicketEventViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect, requires_login]

    @route('participants/checkin', methods=['GET', 'POST'])
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
                    participant_ids=ticket_participant_ids,
                    checked_in=checked_in,
                )
        return redirect(self.obj.url_for('view'), code=303)

    @route('participants/json')
    @render_with(json=True)
    @requires_roles({'project_concierge', 'project_usher'})
    def participants_json(self):
        checkin_count = 0
        participants = []
        for participant in TicketParticipant.checkin_list(self.obj):
            participants.append(
                ticket_participant_checkin_data(participant, self.obj.project, self.obj)
            )
            if participant.checked_in:
                checkin_count += 1

        return {
            'participants': participants,
            'total_participants': len(participants),
            'total_checkedin': checkin_count,
        }

    @route('badges')
    @render_with('badge.html.jinja2')
    @requires_roles({'project_concierge', 'project_usher'})
    def badges(self):
        badge_printed = getbool(request.args.get('badge_printed', 'f'))
        participants = (
            TicketParticipant.query.join(TicketEventParticipant)
            .filter(TicketEventParticipant.ticket_event_id == self.obj.id)
            .filter(TicketParticipant.badge_printed == badge_printed)
            .all()
        )
        return {
            'badge_template': self.obj.badge_template,
            'badges': ticket_participant_badge_data(participants, self.obj.project),
        }

    @route('label_badges')
    @render_with('label_badge.html.jinja2')
    @requires_roles({'project_concierge', 'project_usher'})
    def label_badges(self):
        badge_printed = getbool(request.args.get('badge_printed', 'f'))
        participants = (
            TicketParticipant.query.join(TicketEventParticipant)
            .filter(TicketEventParticipant.ticket_event_id == self.obj.id)
            .filter(TicketParticipant.badge_printed == badge_printed)
            .all()
        )
        return {
            'badge_template': self.obj.badge_template,
            'badges': ticket_participant_badge_data(participants, self.obj.project),
        }


@route('/<project>/event/<name>', subdomain='<profile>')
class FunnelTicketEventParticipantView(TicketEventParticipantView):
    pass


TicketEventParticipantView.init_app(app)
FunnelTicketEventParticipantView.init_app(funnelapp)


# FIXME: make this endpoint use uuid_b58 instead of puk, along with badge generation
@route('/<profile>/<project>/event/<event>/participant/<puk>')
class TicketEventParticipantCheckinView(ClassView):
    __decorators__ = [requires_login]

    @route('checkin', methods=['POST'])
    @render_with(json=True)
    def checkin_puk(self, profile, project, event, puk):
        # checked_in = getbool(request.form.get('checkin', 't'))
        # event = (
        #     Event.query.join(Project, Profile)
        #     .filter(
        #         db.func.lower(Profile.name) == db.func.lower(profile),
        #         Project.name == project,
        #         Event.name == event,
        #     )
        #     .first_or_404()
        # )
        # participant = (
        #     Participant.query.join(Project, Profile)
        #     .filter(
        #         db.func.lower(Profile.name) == db.func.lower(profile),
        #         Project.name == project,
        #         Participant.puk == puk,
        #     )
        #     .first_or_404()
        # )
        # attendee = Attendee.get(event, participant.uuid_b58)
        # if not attendee:
        #     return (
        #         {'error': 'not_found', 'error_description': "Attendee not found"},
        #         404,
        #     )
        # attendee.checked_in = checked_in
        # db.session.commit()
        # return {'attendee': {'fullname': participant.fullname}}

        # FIXME: This view and badge generation need to be moved to use base58
        abort(403)


TicketEventParticipantCheckinView.init_app(app)
