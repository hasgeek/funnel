# -*- coding: utf-8 -*-
from flask import flash, redirect, render_template, request, g, url_for, jsonify, make_response
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from baseframe import _
from baseframe import forms
from baseframe.forms import render_form
from coaster.views import load_models
from coaster.utils import midnight_to_utc
from .. import app, lastuser
from ..models import (db, Profile, ProposalSpace, Attendee, ProposalSpaceRedirect, Participant, Event, ContactExchange, SyncTicket)
from ..forms import ParticipantForm
from funnel.util import split_name, format_twitter_handle, make_qrcode


def participant_badge_data(participants, space):
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


def participant_data(participant, space_id, full=False):
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
            'space_id': space_id
        }
    else:
        return {
            '_id': participant.id,
            'puk': participant.puk,
            'fullname': participant.fullname,
            'job_title': participant.job_title,
            'company': participant.company,
            'space_id': space_id
        }


def participant_checkin_data(participant, space, event):
    return {
        'pid': participant.id,
        'fullname': participant.fullname,
        'company': participant.company,
        'email': participant.email,
        'badge_printed': participant.badge_printed,
        'checked_in': participant.checked_in,
        'ticket_type_titles': participant.ticket_type_titles
    }


@app.route('/<space>/participants/json', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def participants_json(profile, space):
    return jsonify(participants=[participant_data(participant, space.id) for participant in space.participants])


@app.route('/<space>/participants/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-participant')
def new_participant(profile, space):
    form = ParticipantForm()
    form.events.query = space.events
    if form.validate_on_submit():
        participant = Participant(proposal_space=space)
        form.populate_obj(participant)
        try:
            db.session.add(participant)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(_(u"This participant already exists."), 'info')
        return redirect(space.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"New Participant"), submit=_(u"Add Participant"))


@app.route('/<space>/participant/<participant_id>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='edit-participant')
def participant_edit(profile, space, participant):
    form = ParticipantForm(obj=participant, model=Participant)
    form.events.query = space.events
    if form.validate_on_submit():
        form.populate_obj(participant)
        db.session.commit()
        flash(_(u"Your changes have been saved"), 'info')
        return redirect(space.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"Edit Participant"), submit=_(u"Save changes"))


@app.route('/<space>/participant', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def participant(profile, space):
    if space.date_upto:
        if midnight_to_utc(space.date_upto + timedelta(days=1), space.timezone, naive=True) < datetime.utcnow():
            return jsonify(message=u"This event has concluded", code=401)
    participant = Participant.query.filter_by(puk=request.args.get('puk')).first()
    if not participant:
        return jsonify(message=u"Not found", code=404)
    elif participant.key == request.args.get('key'):
        try:
            contact_exchange = ContactExchange(user_id=g.user.id, participant_id=participant.id, proposal_space_id=space.id)
            db.session.add(contact_exchange)
            db.session.commit()
        except IntegrityError:
            app.logger.warning(u"Contact Exchange already present")
            db.session.rollback()
        return jsonify(participant=participant_data(participant, space.id, full=True))
    else:
        return jsonify(message=u"Unauthorized", code=401)


@app.route('/<space>/participant/<participant_id>/badge', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='view-participant')
def participant_badge(profile, space, participant):
    return render_template('badge.html.jinja2', badges=participant_badge_data([participant], space))


@app.route('/<space>/event/<name>/checkin/<participant_id>', methods=['POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'name': 'name', 'proposal_space': 'space'}, 'event'),
    permission='checkin-event')
def event_checkin(profile, space, event):
    form = forms.Form()
    if form.validate_on_submit():
        checked_in = True if request.form.get('checkin') == 't' else False
        participant_ids = request.form.getlist('pid')
        for participant_id in participant_ids:
            participant = Participant.query.filter_by(id=participant_id).first()
            attendee = Attendee.get(event, participant)
            attendee.checked_in = checked_in
        db.session.commit()
        if request.is_xhr:
            return jsonify(status=True, participant_ids=participant_ids, checked_in=checked_in)
    return redirect(url_for('event', profile=space.profile.name, space=space.name, name=event.name), code=303)


@app.route('/<space>/event/<name>/checkin/api', methods=['POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'name': 'name', 'proposal_space': 'space'}, 'event'),
    permission='checkin-event')
def checkin_puk(profile, space, event):
    checked_in = True if request.form.get('checkin') == 't' else False
    participant_puks = request.form.getlist('puk')
    attendees = []
    for participant_puk in participant_puks:
        participant = Participant.query.filter_by(puk=participant_puk).first()
        attendee = Attendee.get(event, participant)
        if not attendee:
            return make_response(jsonify(error='not_found', error_description="Attendee not found"), 404)
        attendee.checked_in = checked_in
        attendees.append({
            'puk': participant_puk,
            'fullname': participant.fullname,
            'checked_in': attendee.checked_in
            })
    db.session.commit()
    return jsonify(result=attendees)


@app.route('/<space>/event/<name>/participants/json', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'name': 'name', 'proposal_space': 'space'}, 'event'),
    permission='checkin-event')
def event_participants_json(profile, space, event):
    checkin_count = 0
    participants = []
    for participant in Participant.checkin_list(event):
        participants.append(participant_checkin_data(participant, space, event))
        if participant.checked_in:
            checkin_count += 1

    return jsonify(participants=participants, total_participants=len(participants), total_checkedin=checkin_count)


@app.route('/<space>/event/<name>/badges', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'name': 'name', 'proposal_space': 'space'}, 'event'),
    permission='view-event')
def event_badges(profile, space, event):
    badge_printed = True if request.args.get('badge_printed') == 't' else False
    participants = Participant.query.join(Attendee).filter(Attendee.event_id == event.id).filter(Participant.badge_printed == badge_printed).all()
    return render_template('badge.html.jinja2', badges=participant_badge_data(participants, space))
