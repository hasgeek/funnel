# -*- coding: utf-8 -*-

from collections import namedtuple

from sqlalchemy.exc import IntegrityError

from flask import flash, g, jsonify, redirect, request, url_for

from baseframe import _, forms
from baseframe.forms import render_form
from coaster.auth import current_auth
from coaster.utils import getbool, uuid2suuid
from coaster.views import (
    ClassView,
    ModelView,
    UrlForView,
    render_with,
    requires_permission,
    route,
)

from .. import app, funnelapp
from ..forms import ParticipantForm
from ..models import Attendee, Event, Participant, Profile, Project, SyncTicket, db
from ..utils import format_twitter_handle, make_qrcode, split_name, strip_null
from ..views.helpers import mask_email
from .decorators import legacy_redirect
from .helpers import requires_login
from .mixins import EventViewMixin, ProjectViewMixin

EventParticipant = namedtuple('EventParticipant', ['event', 'participant'])


def participant_badge_data(participants, project):
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


def participant_data(participant, project_id, full=False):
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


def participant_checkin_data(participant, project, event):
    psuuid = uuid2suuid(participant.uuid)
    data = {
        'psuuid': psuuid,
        'fullname': participant.fullname,
        'company': participant.company,
        'email': mask_email(participant.email),
        'badge_printed': participant.badge_printed,
        'checked_in': participant.checked_in,
        'ticket_type_titles': participant.ticket_type_titles,
    }
    if 'checkin_event' in current_auth.user.current_permissions:
        data.update(
            {
                'badge_url': url_for(
                    'ParticipantView_badge',
                    profile=project.profile.name,
                    project=project.name,
                    participant=psuuid,
                ),
                'label_badge_url': url_for(
                    'ParticipantView_label_badge',
                    profile=project.profile.name,
                    project=project.name,
                    participant=psuuid,
                ),
                'edit_url': url_for(
                    'ParticipantView_edit',
                    profile=project.profile.name,
                    project=project.name,
                    participant=psuuid,
                ),
            }
        )
    return data


@route('/<profile>/<project>/participants')
class ProjectParticipantView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('new-participant')
    def new_participant(self):
        form = ParticipantForm(parent=self.obj)
        if form.validate_on_submit():
            participant = Participant(project=self.obj)
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
class FunnelProjectParticipantView(ProjectParticipantView):
    pass


ProjectParticipantView.init_app(app)
FunnelProjectParticipantView.init_app(funnelapp)


@route('/<profile>/<project>/participant/<participant>')
class ParticipantView(UrlForView, ModelView):
    __decorators__ = [legacy_redirect, requires_login]

    model = Participant
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'participant': 'suuid',
    }

    def loader(self, profile, project, participant):
        participant = (
            self.model.query.join(Project, Profile)
            .filter(
                Profile.name == profile,
                Project.name == project,
                Participant.suuid == participant,
            )
            .first_or_404()
        )
        return participant

    def after_loader(self):
        g.profile = self.obj.project.profile
        return super(ParticipantView, self).after_loader()

    @route('edit', methods=['GET', 'POST'])
    @requires_permission('edit-participant')
    def edit(self):
        form = ParticipantForm(obj=self.obj, parent=self.obj.project)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_(u"Your changes have been saved"), 'info')
            return redirect(self.obj.project.url_for('admin'), code=303)
        return render_form(
            form=form, title=_(u"Edit Participant"), submit=_(u"Save changes")
        )

    @route('badge', methods=['GET'])
    @render_with('badge.html.jinja2')
    @requires_permission('checkin_event')
    def badge(self):
        return {'badges': participant_badge_data([self.obj], self.obj.project)}

    @route('label_badge', methods=['GET'])
    @render_with('label_badge.html.jinja2')
    @requires_permission('checkin_event')
    def label_badge(self):
        return {'badges': participant_badge_data([self.obj], self.obj.project)}


@route('/<project>/participant/<suuid>', subdomain='<profile>')
class FunnelParticipantView(ParticipantView):
    pass


ParticipantView.init_app(app)
FunnelParticipantView.init_app(funnelapp)


@route('/<profile>/<project>/event/<name>')
class EventParticipantView(EventViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect, requires_login]

    @route('participants/checkin', methods=['GET', 'POST'])
    @requires_permission('checkin_event')
    def checkin(self):
        form = forms.Form()
        if form.validate_on_submit():
            checked_in = getbool(request.form.get('checkin'))
            participant_ids = [strip_null(x) for x in request.form.getlist('psuuid')]
            for participant_id in participant_ids:
                attendee = Attendee.get(self.obj, participant_id)
                attendee.checked_in = checked_in
            db.session.commit()
            if request.is_xhr:
                return jsonify(
                    status=True, participant_ids=participant_ids, checked_in=checked_in
                )
        return redirect(self.obj.url_for('view'), code=303)

    @route('participants/json')
    @render_with(json=True)
    @requires_permission('checkin_event')
    def participants_json(self):
        checkin_count = 0
        participants = []
        for participant in Participant.checkin_list(self.obj):
            participants.append(
                participant_checkin_data(participant, self.obj.project, self.obj)
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
    @requires_permission('checkin_event')
    def badges(self):
        badge_printed = getbool(request.args.get('badge_printed', 'f'))
        participants = (
            Participant.query.join(Attendee)
            .filter(Attendee.event_id == self.obj.id)
            .filter(Participant.badge_printed == badge_printed)
            .all()
        )
        return {
            'badge_template': self.obj.badge_template,
            'badges': participant_badge_data(participants, self.obj.project),
        }

    @route('label_badges')
    @render_with('label_badge.html.jinja2')
    @requires_permission('checkin_event')
    def label_badges(self):
        badge_printed = getbool(request.args.get('badge_printed', 'f'))
        participants = (
            Participant.query.join(Attendee)
            .filter(Attendee.event_id == self.obj.id)
            .filter(Participant.badge_printed == badge_printed)
            .all()
        )
        return {
            'badge_template': self.obj.badge_template,
            'badges': participant_badge_data(participants, self.obj.project),
        }


@route('/<project>/event/<name>', subdomain='<profile>')
class FunnelEventParticipantView(EventParticipantView):
    pass


EventParticipantView.init_app(app)
FunnelEventParticipantView.init_app(funnelapp)


# FIXME: make this endpoint use suuid instead of puk, along with badge generation
@route('/<profile>/<project>/event/<event>/participant/<puk>')
class EventParticipantCheckinView(ClassView):
    __decorators__ = [requires_login]

    @route('checkin', methods=['POST'])
    @render_with(json=True)
    def checkin_puk(self, profile, project, event, puk):
        checked_in = getbool(request.form.get('checkin', 't'))
        event = (
            Event.query.join(Project, Profile)
            .filter(
                Profile.name == profile, Project.name == project, Event.name == event
            )
            .first_or_404()
        )
        participant = (
            Participant.query.join(Project, Profile)
            .filter(
                Profile.name == profile, Project.name == project, Participant.puk == puk
            )
            .first_or_404()
        )
        attendee = Attendee.get(event, participant.suuid)
        if not attendee:
            return (
                {'error': 'not_found', 'error_description': "Attendee not found"},
                404,
            )
        attendee.checked_in = checked_in
        db.session.commit()
        return {'attendee': {'fullname': participant.fullname}}


EventParticipantCheckinView.init_app(app)
