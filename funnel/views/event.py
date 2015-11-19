# -*- coding: utf-8 -*-
from flask import redirect, render_template, url_for, flash
from coaster.views import load_models
from sqlalchemy.exc import IntegrityError
from .. import app, lastuser
from ..models import (db, Profile, ProposalSpace, ProposalSpaceRedirect, Participant, Event, TicketType, TicketClient)
from baseframe import forms
from baseframe import _
from baseframe.forms import render_form
from ..forms import EventForm, TicketTypeForm, ParticipantBadgeForm, TicketClientForm
from ..jobs import import_tickets


@app.route('/<space>/admin', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='admin')
def admin(profile, space):
    attendee_sync_form = forms.Form()
    if attendee_sync_form.validate_on_submit():
        for ticket_client in space.ticket_clients:
            if ticket_client and ticket_client.name == u'explara':
                import_tickets.delay(app.config['ENV'], ticket_client.id)
        flash(_(u"Importing tickets from vendors...Refresh the page in about 30 seconds..."), 'info')
        return redirect(space.url_for('admin'), code=303)
    return render_template('admin.html', profile=profile, space=space, events=space.events, attendee_sync_form=attendee_sync_form)


@app.route('/<space>/events/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-event')
def new_event(profile, space):
    form = EventForm()
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
        return redirect(space.url_for('admin'), code=303)
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
    if form.validate_on_submit():
        form.populate_obj(event)
        db.session.commit()
        flash(_(u"Your changes have been saved"), 'info')
        return redirect(space.url_for('admin'), code=303)
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


@app.route('/<space>/ticket_type/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-ticket-type')
def new_ticket_type(profile, space):
    form = TicketTypeForm()
    form.events.query = space.events
    if form.validate_on_submit():
        ticket_type = TicketType(proposal_space=space)
        form.populate_obj(ticket_type)
        ticket_type.make_name()
        try:
            db.session.add(ticket_type)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(_(u"This ticket type already exists."), 'info')
        return redirect(space.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"New Ticket Type"), submit=_(u"Add ticket type"))


@app.route('/<space>/ticket_type/<name>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (TicketType, {'name': 'name', 'proposal_space': 'space'}, 'ticket_type'),
    permission='event-edit')
def ticket_type_edit(profile, space, ticket_type):
    form = TicketTypeForm(obj=ticket_type, model=TicketType)
    form.events.query = space.events
    if form.validate_on_submit():
        form.populate_obj(ticket_type)
        db.session.commit()
        flash(_(u"Your changes have been saved"), 'info')
        return redirect(space.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"Edit ticket type"), submit=_(u"Save changes"))


@app.route('/<space>/ticket_client/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-ticket-client')
def new_ticket_client(profile, space):
    form = TicketClientForm()
    if form.validate_on_submit():
        ticket_client = TicketClient(proposal_space=space)
        form.populate_obj(ticket_client)
        try:
            db.session.add(ticket_client)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(_(u"This ticket client already exists."), 'info')
        return redirect(space.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"New Ticket Client"), submit=_(u"Add Ticket Client"))


@app.route('/<space>/ticket_client/<id>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (TicketClient, {'id': 'id', 'proposal_space': 'space'}, 'ticket_client'),
    permission='ticket-client-edit')
def ticket_client_edit(profile, space, ticket_client):
    form = TicketClientForm(obj=ticket_client, model=TicketClient)
    if form.validate_on_submit():
        form.populate_obj(ticket_client)
        db.session.commit()
        flash(_(u"Your changes have been saved"), 'info')
        return redirect(space.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"Edit ticket client"), submit=_(u"Save changes"))


@app.route('/<space>/event/<name>', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'name': 'name', 'proposal_space': 'space'}, 'event'),
    permission='event-view')
def event(profile, space, event):
    participants = Participant.checkin_list(event)
    form = ParticipantBadgeForm()
    if form.validate_on_submit():
        badge_printed = True if form.data.get('badge_printed') == 't' else False
        db.session.query(Participant).filter(Participant.id.in_([participant.id for participant in event.participants])).\
            update({'badge_printed': badge_printed}, False)
        db.session.commit()
        return redirect(url_for('event', profile=space.profile.name, space=space.name, name=event.name), code=303)
    return render_template('event.html', profile=profile, space=space, event=event, badge_form=ParticipantBadgeForm(model=Participant))
