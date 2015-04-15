# -*- coding: utf-8 -*-

from flask import flash, redirect, render_template, request, abort
from baseframe import _
from baseframe.forms import render_form
from coaster.views import load_models, jsonp

from .. import app, lastuser
from ..models import (db, Profile, ProposalSpace, ProposalSpaceRedirect, Participant, Event, Attendee)
from ..forms import ParticipantForm
from helpers import split_name, format_twitter, make_qrcode


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


@app.route('/<space>/participants/json', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def participants_json(profile, space):
    return jsonp(participants=[participant_data(participant, space.id) for participant in space.participants])


@app.route('/<space>/participants/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-participant')
def new_participant(profile, space):
    form = ParticipantForm()
    if form.validate_on_submit():
        participant = Participant(proposal_space=space)
        form.populate_obj(participant)
        db.session.add(participant)
        db.session.commit()
        return redirect(space.url_for(), code=303)
    return render_form(form=form, title=_("New Participant"), submit=_("Add Participant"))


@app.route('/<space>/participant/<participant_id>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='participant-edit')
def participant_edit(profile, space, participant):
    form = ParticipantForm(obj=participant, model=Participant)
    if form.validate_on_submit():
        form.populate_obj(participant)
        db.session.commit()
        flash(_("Your changes have been saved"), 'info')
        return redirect(space.url_for('events'), code=303)
    return render_form(form=form, title=_("Edit Participant"), submit=_("Save changes"))


@app.route('/<space>/participant', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def participant(profile, space):
    participant = Participant.query.filter_by(puk=request.args.get('puk')).first()
    if not participant:
        return jsonp(message="Not found", code=404)
    elif participant.key == request.args.get('key'):
        # TODO: add contact
        return jsonp(participant=participant_data(participant, space.id, full=True))
    else:
        return jsonp(message="Unauthorized", code=401)


@app.route('/<space>/event', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='event-view')
def events(profile, space):
    return render_template('events.html', profile=profile, space=space, events=space.events.all())


@app.route('/<space>/event/<event_id>', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'id': 'event_id'}, 'event'),
    permission='event-view')
def event(profile, space, event):
    participants = Participant.attendees_by_event(event)
    return render_template('event.html', profile=profile, space=space, participants=participants, event=event)


def participant_badge_data(participants, space):
    badges = []
    for participant in participants:
        qrcode_data = "{0}{1}".format(participant.puk, participant.key)
        qrcode_path = "{0}/{1}_{2}_{3}.{4}".format(app.config.get('BADGES_PATH'), space.profile.name, space.name, str(participant.puk), 'svg')
        first_name, last_name = split_name(participant.fullname)
        badges.append({
            'first_name': first_name,
            'last_name': last_name,
            'twitter': format_twitter(participant.twitter),
            'company': participant.company,
            'qrcode_content': make_qrcode(qrcode_data, qrcode_path)
        })
    return badges


@app.route('/<space>/event/<event_id>/badges', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'id': 'event_id'}, 'event'),
    permission='event-view')
def event_badges(profile, space, event):
    badge_printed = True if request.args.get('badge_printed') == 't' else False
    participants = Participant.query.join(Attendee).filter(Attendee.event_id == event.id).filter(Participant.badge_printed == badge_printed).all()
    return render_template('badge.html', badges=participant_badge_data(participants, space))


@app.route('/<space>/participant/<participant_id>/badge', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='participant-view')
def participant_badge(profile, space, participant):
    return render_template('badge.html', badges=participant_badge_data([participant], space))


@app.route('/<space>/event/<event_id>/checkin/<participant_id>', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'id': 'event_id'}, 'event'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='event-checkin')
def event_checkin(profile, space, event, participant):
    a = Attendee.query.filter_by(participant_id=participant.id, event_id=event.id).first()
    checked_in = True if request.args.get('checkin') == 't' else False
    a.checked_in = checked_in
    db.session.add(a)
    db.session.commit()
    return redirect("{0}event/{1}".format(space.url_for(), event.id), code=303)
