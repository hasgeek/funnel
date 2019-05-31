# -*- coding: utf-8 -*-
from flask import flash, redirect, render_template, request, url_for, jsonify, make_response, current_app
from datetime import timedelta
from sqlalchemy.exc import IntegrityError
from baseframe import _
from baseframe import forms
from baseframe.forms import render_form
from coaster.auth import current_auth
from coaster.views import load_models, requestargs, route, requires_permission, UrlForView, ModelView
from coaster.utils import midnight_to_utc, getbool, utcnow
from .. import app, funnelapp, lastuser
from ..models import (db, Profile, Project, Attendee, ProjectRedirect, Participant, Event, ContactExchange, SyncTicket)
from ..forms import ParticipantForm
from ..views.helpers import mask_email
from funnel.util import split_name, format_twitter_handle, make_qrcode
from .project import ProjectViewMixin
from .decorators import legacy_redirect


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


@app.route('/participant', methods=['GET', 'POST'])
@funnelapp.route('/participant', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@requestargs('puk', 'key')
def participant(puk, key):
    """
    Endpoint for contact exchange.

    TODO: The GET method to this endpoint is deprecated and will be removed by 1st September, 2018
    """
    participant = Participant.query.filter_by(puk=puk, key=key).first()
    if not participant:
        return make_response(jsonify(status='error', message=u"Participant not found"), 404) 
    project = participant.project
    if project.date_upto:
        if midnight_to_utc(project.date_upto + timedelta(days=1), project.timezone) < utcnow():
            return make_response(jsonify(status='error', message=u"This event has concluded"), 401)

        try:
            contact_exchange = ContactExchange(user=current_auth.actor, participant=participant)
            db.session.add(contact_exchange)
            db.session.commit()
        except IntegrityError:
            current_app.logger.warning(u"Contact Exchange already present")
            db.session.rollback()
        return jsonify(participant=participant_data(participant, project.id, full=True))
    else:
        return make_response(jsonify(status='error', message=u"Unauthorized contact exchange"), 401)


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
