# -*- coding: utf-8 -*-
from rq import Queue
from redis import Redis
from flask import redirect, render_template, url_for, flash, jsonify
from coaster.views import load_models
from coaster.utils import getbool
from sqlalchemy.exc import IntegrityError
from .. import app, lastuser
from ..models import (db, Profile, ProposalSpace, ProposalSpaceRedirect, Participant, Event, TicketType, TicketClient, SyncTicket)
from baseframe import forms
from baseframe import _
from baseframe.forms import render_form
from ..forms import EventForm, TicketTypeForm, ParticipantBadgeForm, TicketClientForm
from ..jobs import import_tickets


redis_connection = Redis()
funnelq = Queue('funnel', connection=redis_connection)


@app.route('/<space>/admin', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='admin')
def admin(profile, space):
    csrf_form = forms.Form()
    if csrf_form.validate_on_submit():
        for ticket_client in space.ticket_clients:
            if ticket_client and ticket_client.name.lower() in [u'explara', u'boxoffice']:
                funnelq.enqueue(import_tickets, ticket_client.id)
        flash(_(u"Importing tickets from vendors...Refresh the page in about 30 seconds..."), 'info')
        return redirect(space.url_for('admin'), code=303)
    return render_template('admin.html.jinja2', profile=profile, space=space, events=space.events, csrf_form=csrf_form)


@app.route('/<space>/events', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='admin')
def events(profile, space):
    return render_template('event_list.html', profile=profile, space=space, events=space.events)


@app.route('/<space>/events/json', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='admin')
def events_json(profile, space):
    events = []
    for event in space.events:
        events.append({
            'title': event.title,
            'name': event.name,
            })
    return jsonify(result=events)


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
    permission='edit-event')
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
    permission='view-ticket-type')
def ticket_type(profile, space, ticket_type):
    participants = Participant.query.join(SyncTicket).filter(SyncTicket.ticket_type == ticket_type).all()
    return render_template('ticket_type.html.jinja2', profile=profile, space=space, ticket_type=ticket_type, participants=participants)


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
    permission='edit-event')
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
    permission='edit-ticket-client')
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
    permission='view-event')
def event(profile, space, event):
    form = ParticipantBadgeForm()
    if form.validate_on_submit():
        badge_printed = True if getbool(form.data.get('badge_printed')) else False
        db.session.query(Participant).filter(Participant.id.in_([participant.id for participant in event.participants])).\
            update({'badge_printed': badge_printed}, False)
        db.session.commit()
        return redirect(url_for('event', profile=space.profile.name, space=space.name, name=event.name), code=303)
    return render_template('event.html', profile=profile, space=space, event=event, badge_form=ParticipantBadgeForm(model=Participant), checkin_form=forms.Form())


@app.route('/<space>/event/<name>/scan_badge', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'name': 'name', 'proposal_space': 'space'}, 'event'),
    permission='view-event')
def scan_badge(profile, space, event):
    return render_template('scan_badge.html', profile=profile, space=space, event=event)
