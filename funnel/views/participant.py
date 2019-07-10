# -*- coding: utf-8 -*-
from sqlalchemy.exc import IntegrityError

from flask import (
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from baseframe import _, forms
from baseframe.forms import render_form
from coaster.utils import getbool
from coaster.views import ModelView, UrlForView, load_models, requires_permission, route
from funnel.util import format_twitter_handle, make_qrcode, split_name

from .. import app, funnelapp, lastuser
from ..forms import ParticipantForm
from ..models import (
    Attendee,
    Event,
    Participant,
    Profile,
    Project,
    ProjectRedirect,
    SyncTicket,
    db,
)
from ..views.helpers import mask_email
from .decorators import legacy_redirect
from .project import ProjectViewMixin


def participant_badge_data(participants, project):
    badges = []
    for participant in participants:
        first_name, last_name = split_name(participant.fullname)
        ticket = SyncTicket.query.filter_by(participant=participant).first()
        badges.append({
            'first_name': first_name,
            'last_name': last_name,
            'twitter': format_twitter_handle(participant.twitter),
            'company': participant.company,
            'qrcode_content': make_qrcode(u"{puk}{key}".format(puk=participant.puk, key=participant.key)),
            'order_no': ticket.order_no if ticket else ''
            })
    return badges


def participant_data(participant, project_id, full=False):
    if full:
        return {
            '_id': participant.id,
            'puk': participant.puk,
            'fullname': participant.fullname,
            'job_title': participant.job_title,
            'company': participant.company,
            'email': participant.email,
            'twitter': participant.twitter,
            'phone': participant.phone,
            'project_id': project_id,
            'space_id': project_id,  # FIXME: Remove when the native app switches over
            }
    else:
        return {
            '_id': participant.id,
            'puk': participant.puk,
            'fullname': participant.fullname,
            'job_title': participant.job_title,
            'company': participant.company,
            'project_id': project_id,
            'space_id': project_id,  # FIXME: Remove when the native app switches over
            }


def participant_checkin_data(participant, project, event):
    return {
        'pid': participant.id,
        'fullname': participant.fullname,
        'company': participant.company,
        'email': mask_email(participant.email),
        'badge_printed': participant.badge_printed,
        'checked_in': participant.checked_in,
        'ticket_type_titles': participant.ticket_type_titles
        }


@route('/<profile>/<project>/participants')
class ProjectParticipantView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('json')
    @lastuser.requires_login
    @requires_permission('view')
    def participants_json(self):
        return jsonify(participants=[participant_data(participant, self.obj.id) for participant in self.obj.participants])

    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new-participant')
    def new_participant(self):
        form = ParticipantForm()
        form.events.query = self.obj.events
        if form.validate_on_submit():
            participant = Participant(project=self.obj)
            form.populate_obj(participant)
            try:
                db.session.add(participant)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(_(u"This participant already exists."), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(form=form, title=_(u"New Participant"), submit=_(u"Add Participant"))


@route('/<project>/participants', subdomain='<profile>')
class FunnelProjectParticipantView(ProjectParticipantView):
    pass


ProjectParticipantView.init_app(app)
FunnelProjectParticipantView.init_app(funnelapp)


@app.route('/<profile>/<project>/participant/<participant_id>/edit', methods=['GET', 'POST'])
@funnelapp.route('/<project>/participant/<participant_id>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='edit-participant')
def participant_edit(profile, project, participant):
    form = ParticipantForm(obj=participant, model=Participant)
    form.events.query = project.events
    if form.validate_on_submit():
        form.populate_obj(participant)
        db.session.commit()
        flash(_(u"Your changes have been saved"), 'info')
        return redirect(project.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"Edit Participant"), submit=_(u"Save changes"))


@app.route('/<profile>/<project>/participant/<participant_id>/badge')
@funnelapp.route('/<project>/participant/<participant_id>/badge', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='checkin_event')
def participant_badge(profile, project, participant):
    return render_template('badge.html.jinja2',
        badges=participant_badge_data([participant], project))


@app.route('/<profile>/<project>/event/<name>/participants/checkin', methods=['POST'])
@funnelapp.route('/<project>/event/<name>/participants/checkin', methods=['POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Event, {'name': 'name', 'project': 'project'}, 'event'),
    permission='checkin_event')
def event_checkin(profile, project, event):
    form = forms.Form()
    if form.validate_on_submit():
        checked_in = getbool(request.form.get('checkin'))
        participant_ids = request.form.getlist('pid')
        for participant_id in participant_ids:
            attendee = Attendee.get(event, participant_id)
            attendee.checked_in = checked_in
        db.session.commit()
        if request.is_xhr:
            return jsonify(status=True, participant_ids=participant_ids, checked_in=checked_in)
    return redirect(url_for('event', profile=project.profile.name, project=project.name, name=event.name), code=303)


@app.route('/<profile>/<project>/event/<name>/participant/<puk>/checkin', methods=['POST'])
@funnelapp.route('/<project>/event/<name>/participant/<puk>/checkin', methods=['POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Event, {'name': 'name', 'project': 'project'}, 'event'),
    (Participant, {'puk': 'puk'}, 'participant'),
    permission='checkin_event')
def checkin_puk(profile, project, event, participant):
    checked_in = getbool(request.form.get('checkin'))
    attendee = Attendee.get(event, participant.id)
    if not attendee:
        return make_response(jsonify(error='not_found', error_description="Attendee not found"), 404)
    attendee.checked_in = checked_in
    db.session.commit()
    return jsonify(attendee={'fullname': participant.fullname})


@app.route('/<profile>/<project>/event/<name>/participants/json')
@funnelapp.route('/<project>/event/<name>/participants/json', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Event, {'name': 'name', 'project': 'project'}, 'event'),
    permission='checkin_event')
def event_participants_json(profile, project, event):
    checkin_count = 0
    participants = []
    for participant in Participant.checkin_list(event):
        participants.append(participant_checkin_data(participant, project, event))
        if participant.checked_in:
            checkin_count += 1

    return jsonify(participants=participants, total_participants=len(participants), total_checkedin=checkin_count)


@app.route('/<profile>/<project>/event/<name>/badges')
@funnelapp.route('/<project>/event/<name>/badges', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Event, {'name': 'name', 'project': 'project'}, 'event'),
    permission='checkin_event')
def event_badges(profile, project, event):
    badge_printed = True if request.args.get('badge_printed') == 't' else False
    participants = Participant.query.join(Attendee).filter(Attendee.event_id == event.id).filter(Participant.badge_printed == badge_printed).all()
    return render_template('badge.html.jinja2', badge_template=event.badge_template,
        badges=participant_badge_data(participants, project))
