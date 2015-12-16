# -*- coding: utf-8 -*-
from flask import flash, redirect, render_template, request, g, url_for, jsonify
from sqlalchemy.exc import IntegrityError
from baseframe import _
from baseframe import forms
from baseframe.forms import render_form
from coaster.views import load_models
from .. import app, lastuser
from ..models import (db, Profile, ProposalSpace, Attendee, ProposalSpaceRedirect, Participant, Event, ContactExchange)
from ..forms import ParticipantForm, ParticipantImportForm
from funnel.util import split_name, format_twitter_handle, make_qrcode, csv_to_rows


def participant_badge_data(participants, space):
    badges = []
    for participant in participants:
        first_name, last_name = split_name(participant.fullname)
        badges.append({
            'first_name': first_name,
            'last_name': last_name,
            'twitter': format_twitter_handle(participant.twitter),
            'company': participant.company,
            'qrcode_content': make_qrcode(u"{puk}{key}".format(puk=participant.puk, key=participant.key))
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
            # db.session().add_and_commit(participant)
            db.session.add(participant)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(_(u"This participant already exists."), 'info')
        return redirect(space.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"New Participant"), submit=_(u"Add Participant"))


@app.route('/<space>/participants/import', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-participant')
def import_participant(profile, space):
    form = ParticipantImportForm()
    form.events.query = space.events
    if form.validate_on_submit():
        participant_list_csv = request.files['participant_list']
        rows = csv_to_rows(participant_list_csv.read())
        if participant_list_csv and rows and rows[0].get('email') and rows[0].get('fullname'):
            for row in rows:
                fields = {'events': form.data['events'], 'fullname': row.get('fullname'), 'phone': row.get('phone'), 'twitter': row.get('twitter'), 'company': row.get('company'), 'job_title': row.get('job_title'), 'city': row.get('city')}
                Participant.upsert(space, row.get('email'), **fields)
            db.session.commit()
            flash(_(u"Participants were imported from {filename}".format(filename=participant_list_csv.filename)), 'info')
            return redirect(space.url_for('admin'), code=303)
        else:
            form.participant_list.errors.append(_(u"Please ensure that the file has the required headers"))
    return render_form(form=form, title=_("Import Participants"), submit=_("Import"))


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
    participant = Participant.query.filter_by(puk=request.args.get('puk')).first()
    if not participant:
        return jsonify(message=u"Not found", code=404)
    elif participant.key == request.args.get('key'):
        try:
            contact_exchange = ContactExchange(user_id=g.user.id, participant_id=participant.id, proposal_space_id=space.id)
            # db.session().add_and_commit(contact_exchange)
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
    return render_template('badge.html', badges=participant_badge_data([participant], space))


@app.route('/<space>/event/<name>/checkin/<participant_id>', methods=['POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'name': 'name', 'proposal_space': 'space'}, 'event'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='checkin-event')
def event_checkin(profile, space, event, participant):
    attendee = Attendee.get(event, participant)
    form = forms.Form()
    if form.validate_on_submit():
        # Toggle check-in status
        attendee.checked_in = not attendee.checked_in
        db.session.commit()
    return redirect(url_for('event', profile=space.profile.name, space=space.name, name=event.name), code=303)


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
    return render_template('badge.html', badges=participant_badge_data(participants, space))
