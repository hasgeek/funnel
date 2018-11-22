# -*- coding: utf-8 -*-
from rq import Queue
from redis import Redis
from flask import redirect, render_template, url_for, flash, jsonify
from coaster.views import load_models
from coaster.utils import getbool
from sqlalchemy.exc import IntegrityError
from .. import app, funnelapp, lastuser
from ..models import (db, Profile, Project, ProjectRedirect, Participant, Event, TicketType, TicketClient, SyncTicket)
from baseframe import forms
from baseframe import _
from baseframe.forms import render_form
from ..forms import EventForm, TicketTypeForm, ParticipantBadgeForm, TicketClientForm
from ..jobs import import_tickets


redis_connection = Redis()
funnelq = Queue('funnel', connection=redis_connection)


@app.route('/<profile>/<project>/admin', methods=['GET', 'POST'])
@funnelapp.route('/<project>/admin', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='admin')
def admin(profile, project):
    csrf_form = forms.Form()
    if csrf_form.validate_on_submit():
        for ticket_client in project.ticket_clients:
            if ticket_client and ticket_client.name.lower() in [u'explara', u'boxoffice']:
                funnelq.enqueue(import_tickets, ticket_client.id)
        flash(_(u"Importing tickets from vendors...Refresh the page in about 30 seconds..."), 'info')
        return redirect(project.url_for('admin'), code=303)
    return render_template('admin.html.jinja2', profile=profile, project=project, events=project.events, csrf_form=csrf_form)


@app.route('/<profile>/<project>/events', methods=['GET', 'POST'])
@funnelapp.route('/<project>/events', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='checkin-event')
def events(profile, project):
    return render_template('event_list.html.jinja2', profile=profile, project=project, events=project.events)


@app.route('/<profile>/<project>/events/json', methods=['GET', 'POST'])
@funnelapp.route('/<project>/events/json', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='admin')
def events_json(profile, project):
    return jsonify(events=[{'name': e.name, 'title': e.title} for e in project.events])


@app.route('/<profile>/<project>/events/new', methods=['GET', 'POST'])
@funnelapp.route('/<project>/events/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='new-event')
def new_event(profile, project):
    form = EventForm()
    if form.validate_on_submit():
        event = Event(project=project)
        form.populate_obj(event)
        event.make_name()
        try:
            db.session.add(event)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(_(u"This event already exists."), 'info')
        return redirect(project.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"New Event"), submit=_(u"Add Event"))


@app.route('/<profile>/<project>/event/<name>/edit', methods=['GET', 'POST'])
@funnelapp.route('/<project>/event/<name>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Event, {'name': 'name', 'project': 'project'}, 'event'),
    permission='edit-event')
def event_edit(profile, project, event):
    form = EventForm(obj=event, model=Event)
    if form.validate_on_submit():
        form.populate_obj(event)
        db.session.commit()
        flash(_(u"Your changes have been saved"), 'info')
        return redirect(project.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"Edit event"), submit=_(u"Save changes"))


@app.route('/<profile>/<project>/ticket_type/<name>', methods=['GET'])
@funnelapp.route('/<project>/ticket_type/<name>', methods=['GET'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (TicketType, {'name': 'name', 'project': 'project'}, 'ticket_type'),
    permission='view-ticket-type')
def ticket_type(profile, project, ticket_type):
    participants = Participant.query.join(SyncTicket).filter(SyncTicket.ticket_type == ticket_type).all()
    return render_template('ticket_type.html.jinja2', profile=profile, project=project, ticket_type=ticket_type, participants=participants)


@app.route('/<profile>/<project>/ticket_type/new', methods=['GET', 'POST'])
@funnelapp.route('/<project>/ticket_type/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='new-ticket-type')
def new_ticket_type(profile, project):
    form = TicketTypeForm()
    form.events.query = project.events
    if form.validate_on_submit():
        ticket_type = TicketType(project=project)
        form.populate_obj(ticket_type)
        ticket_type.make_name()
        try:
            db.session.add(ticket_type)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(_(u"This ticket type already exists."), 'info')
        return redirect(project.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"New Ticket Type"), submit=_(u"Add ticket type"))


@app.route('/<profile>/<project>/ticket_type/<name>/edit', methods=['GET', 'POST'])
@funnelapp.route('/<project>/ticket_type/<name>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (TicketType, {'name': 'name', 'project': 'project'}, 'ticket_type'),
    permission='edit-event')
def ticket_type_edit(profile, project, ticket_type):
    form = TicketTypeForm(obj=ticket_type, model=TicketType)
    form.events.query = project.events
    if form.validate_on_submit():
        form.populate_obj(ticket_type)
        db.session.commit()
        flash(_(u"Your changes have been saved"), 'info')
        return redirect(project.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"Edit ticket type"), submit=_(u"Save changes"))


@app.route('/<profile>/<project>/ticket_client/new', methods=['GET', 'POST'])
@funnelapp.route('/<project>/ticket_client/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='new-ticket-client')
def new_ticket_client(profile, project):
    form = TicketClientForm()
    if form.validate_on_submit():
        ticket_client = TicketClient(project=project)
        form.populate_obj(ticket_client)
        try:
            db.session.add(ticket_client)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(_(u"This ticket client already exists."), 'info')
        return redirect(project.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"New Ticket Client"), submit=_(u"Add Ticket Client"))


@app.route('/<profile>/<project>/ticket_client/<id>/edit', methods=['GET', 'POST'])
@funnelapp.route('/<project>/ticket_client/<id>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (TicketClient, {'id': 'id', 'project': 'project'}, 'ticket_client'),
    permission='edit-ticket-client')
def ticket_client_edit(profile, project, ticket_client):
    form = TicketClientForm(obj=ticket_client, model=TicketClient)
    if form.validate_on_submit():
        form.populate_obj(ticket_client)
        db.session.commit()
        flash(_(u"Your changes have been saved"), 'info')
        return redirect(project.url_for('admin'), code=303)
    return render_form(form=form, title=_(u"Edit ticket client"), submit=_(u"Save changes"))


@app.route('/<profile>/<project>/event/<name>', methods=['GET', 'POST'])
@funnelapp.route('/<project>/event/<name>', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Event, {'name': 'name', 'project': 'project'}, 'event'),
    permission='view-event')
def event(profile, project, event):
    form = ParticipantBadgeForm()
    if form.validate_on_submit():
        badge_printed = True if getbool(form.data.get('badge_printed')) else False
        db.session.query(Participant).filter(Participant.id.in_([participant.id for participant in event.participants])).\
            update({'badge_printed': badge_printed}, False)
        db.session.commit()
        return redirect(url_for('event', profile=project.profile.name, project=project.name, name=event.name), code=303)
    return render_template('event.html.jinja2', profile=profile, project=project, event=event, badge_form=ParticipantBadgeForm(model=Participant), checkin_form=forms.Form())


@app.route('/<profile>/<project>/event/<name>/scan_badge', methods=['GET', 'POST'])
@funnelapp.route('/<project>/event/<name>/scan_badge', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Event, {'name': 'name', 'project': 'project'}, 'event'),
    permission='checkin-event')
def scan_badge(profile, project, event):
    return render_template('scan_badge.html.jinja2', profile=profile, project=project, event=event)
