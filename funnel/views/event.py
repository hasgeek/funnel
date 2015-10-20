# -*- coding: utf-8 -*-
from flask import redirect, render_template, url_for, flash
from coaster.views import load_models
from sqlalchemy.orm import load_only
from sqlalchemy.exc import IntegrityError
from .. import app, lastuser
from ..models import (db, Profile, ProposalSpace, ProposalSpaceRedirect, Participant, Event, TicketType)
from baseframe import forms
from baseframe import _
from baseframe.forms import render_form
from ..forms import EventForm, ParticipantBadgeForm
from ..jobs import import_tickets


@app.route('/<space>/event', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='event-view')
def events(profile, space):
    attendee_sync_form = forms.Form()
    if attendee_sync_form.validate_on_submit():
        for ticket_client in space.ticket_clients:
            import_tickets.delay(app.config['ENV'], ticket_client.id)
        return redirect(space.url_for('events'), code=303)
    event_ticket_type_ids = [ticket_type.id for ticket_type in TicketType.query.filter_by(proposal_space=space).join('events').options(load_only('id')).all()]
    ticket_types = TicketType.query.filter_by(proposal_space=space).filter(~TicketType.id.in_(event_ticket_type_ids))
    return render_template('events.html', profile=profile, space=space, events=space.events, attendee_sync_form=attendee_sync_form, ticket_types=ticket_types)


@app.route('/<space>/events/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-event')
def new_event(profile, space):
    form = EventForm()
    form.ticket_types.query = space.ticket_types
    if form.validate_on_submit():
        event = Event(proposal_space=space)
        form.populate_obj(event)
        event.make_name()
        try:
            db.session.add(event)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(_(u"This event already exists."), 'info')
        return redirect(space.url_for('events'), code=303)
    return render_form(form=form, title=_(u"New Event"), submit=_(u"Add Event"))


@app.route('/<space>/event/<name>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'name': 'name', 'proposal_space': 'space'}, 'event'),
    permission='event-edit')
def event_edit(profile, space, event):
    form = EventForm(obj=event, model=Event)
    form.ticket_types.query = space.ticket_types
    if form.validate_on_submit():
        form.populate_obj(event)
        db.session.commit()
        flash(_(u"Your changes have been saved"), 'info')
        return redirect(space.url_for('events'), code=303)
    return render_form(form=form, title=_(u"Edit event"), submit=_(u"Save changes"))


@app.route('/<space>/ticket_type/<name>', methods=['GET'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (TicketType, {'name': 'name', 'proposal_space': 'space'}, 'ticket_type'),
    permission='ticket-type-view')
def ticket_type(profile, space, ticket_type):
    return render_template('ticket_type.html', profile=profile, space=space, ticket_type=ticket_type, participants=Participant.filter_by_ticket_type(ticket_type))


@app.route('/<space>/event/<name>', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'name': 'name', 'proposal_space': 'space'}, 'event'),
    permission='event-view')
def event(profile, space, event):
    participants = Participant.attendees_by_event(event)
    form = ParticipantBadgeForm()
    checkin_form = forms.Form()
    if form.validate_on_submit():
        badge_printed = True if form.data.get('badge_printed') == 't' else False
        Participant.update_badge_printed(event, badge_printed)
        db.session.commit()
        return redirect(url_for('event', profile=space.profile.name, space=space.name, name=event.name), code=303)
    checked_in_count = len([p for p in participants if p.checked_in])
    return render_template('event.html', profile=profile, space=space, participants=participants, event=event, badge_form=ParticipantBadgeForm(model=Participant), checked_in_count=checked_in_count, checkin_form=checkin_form)
